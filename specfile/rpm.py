# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import contextlib
import io
import logging
import os
import re
import sys
import tempfile
from enum import IntEnum
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import rpm

from specfile.exceptions import MacroRemovalException, RPMException
from specfile.utils import get_filename_from_location

MAX_REMOVAL_RETRIES = 20

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def capture_stderr() -> Iterator[List[bytes]]:
    """
    Context manager for capturing output to stderr. A stderr output of anything run
    in its context will be captured in the target variable of the with statement.

    Yields:
        List of captured lines.
    """
    fileno = sys.__stderr__.fileno()
    with tempfile.TemporaryFile() as stderr, os.fdopen(os.dup(fileno)) as backup:
        sys.stderr.flush()
        os.dup2(stderr.fileno(), fileno)
        data: List[bytes] = []
        try:
            yield data
        finally:
            sys.stderr.flush()
            os.dup2(backup.fileno(), fileno)
            stderr.flush()
            stderr.seek(0, io.SEEK_SET)
            data.extend(stderr.readlines())


class MacroLevel(IntEnum):
    BUILTIN = -20
    DEFAULT = -15
    MACROFILES = -13
    RPMRC = -11
    CMDLINE = -7
    TARBALL = -5
    SPEC = -3
    OLDSPEC = -1
    GLOBAL = 0


class Macro(collections.abc.Hashable):
    """
    Class that represents a RPM macro.

    Attributes:
        name: Name of the macro.
        options: Options (parameters) of the macro.
        body: Macro body.
        level: Macro level (source).
        used: Indicates that the macro has been used (expanded).
    """

    def __init__(
        self,
        name: str,
        options: Optional[str],
        body: str,
        level: MacroLevel,
        used: bool,
    ) -> None:
        self.name = name
        self.options = options
        self.body = body
        self.level = level
        self.used = used

    def _key(self) -> tuple:
        return self.name, self.options, self.body, self.level, self.used

    def __hash__(self) -> int:
        return hash(self._key())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Macro):
            return NotImplemented
        return self._key() == other._key()

    def __repr__(self) -> str:
        options = f"'{self.options}'" if self.options else "None"
        level = repr(self.level)
        return f"Macro('{self.name}', {options}, '{self.body}', {level}, {self.used})"


class Macros:
    @staticmethod
    def _parse(dump: List[str]) -> List[Macro]:
        """
        Parses macros in the format of %dump output.

        Args:
            dump: List of lines in the same format as what the %dump macro outputs
                  to stderr, including newline characters.

        Returns:
            List of `Macro` instances.
        """
        # last line contains only summary
        dump.pop()
        macro_regex = re.compile(
            r"^\s*(?P<l>-?\d+)(?P<u>=|:) (?P<n>\w+)(?P<o>\(.+?\))?\t(?P<b>.*)$"
        )
        result = []
        while dump:
            line = dump.pop(0)
            # join long lines split by \
            while line.endswith("\\\n"):
                line = line[:-2] + dump.pop(0)
            # get rid of newline characters
            line = line[:-1]
            m = macro_regex.match(line)
            if m:
                result.append(
                    Macro(
                        m.group("n"),
                        m.group("o"),
                        m.group("b"),
                        MacroLevel(int(m.group("l"))),
                        m.group("u") == "=",
                    )
                )
            elif result:
                if result[-1].body:
                    result[-1].body += "\n"
                result[-1].body += line
        return result

    @classmethod
    def dump(cls) -> List[Macro]:
        """
        Dumps all macros defined in the global context.

        This is not 100% accurate, since macros can be defined multiple times,
        but only the last definition is listed.

        Returns:
            List of `Macro` instances.
        """
        with capture_stderr() as stderr:
            rpm.expandMacro("%dump")
        return cls._parse([line.decode() for line in stderr])

    @staticmethod
    def expand(expression: str) -> str:
        """
        Expands an expression in the global context.

        Args:
            expression: Expression to expand.

        Returns:
            Expanded expression.

        Raises:
            RPMException, if expansion error occurs.
        """
        try:
            with capture_stderr() as stderr:
                return rpm.expandMacro(expression)
        except rpm.error as e:
            raise RPMException(stderr=stderr) from e

    @classmethod
    def remove(cls, macro: str) -> None:
        """
        Removes all definitions of a macro in the global context.

        Args:
            macro: Macro name.

        Raises:
            MacroRemovalException, if there were too many unsuccessful
                retries to remove the macro.
        """
        # Ideally, we would loop until the macro is defined, however in rpm
        # 4.16, expanding parametrized macros may throw an exception
        # which would result in an infinite loop. Limit the number of iterations.
        retry = 0
        while retry < MAX_REMOVAL_RETRIES:
            rpm.delMacro(macro)
            try:
                if cls.expand(f"%{macro}") == f"%{macro}":
                    break
            except RPMException:
                # the macro can't be expanded, but it still exists
                retry += 1
                continue
        else:
            raise MacroRemovalException(
                f"Max attempts for removal ({MAX_REMOVAL_RETRIES}) exceeded"
            )

    @classmethod
    def define(cls, macro: str, body: str) -> None:
        """
        Defines a macro in the global context.

        Removes all existing definitions first. It is not possible to define a macro
        with options. The new macro will always have `MacroLevel.OLDSPEC` level.

        Args:
            macro: Macro name.
            body: Macro body.
        """
        cls.remove(macro)
        rpm.addMacro(macro, body)

    @classmethod
    def reinit(cls, level_threshold: MacroLevel = MacroLevel.RPMRC) -> None:
        """
        Reinitializes macros in the global context.

        Args:
            level_threshold: Only macros up to this level remain defined.
        """
        # reset everything, including macros
        rpm.reloadConfig()
        for macro in cls.dump():
            if macro.level > level_threshold:
                cls.remove(macro.name)


class SpecParser:
    """
    Class that represents a spec file parser.

    Attributes:
        sourcedir: Path to sources and patches.
        macros: List of extra macro definitions.
        ignore_missing_includes: Whether to attempt to parse the spec file even if one
          or more files to be included using the %include directive are not available.
        spec: `rpm.spec` instance representing parsed spec file.
        tainted: Indication that the spec file wasn't parsed completely and at least
          one file to be included was ignored.
    """

    def __init__(
        self,
        sourcedir: Path,
        macros: Optional[List[Tuple[str, str]]] = None,
        ignore_missing_includes: bool = False,
    ) -> None:
        self.sourcedir = sourcedir
        self.macros = macros.copy() if macros is not None else []
        self.ignore_missing_includes = ignore_missing_includes
        self.spec = None
        self.tainted = False

    def __repr__(self) -> str:
        sourcedir = repr(self.sourcedir)
        macros = repr(self.macros)
        ignore_missing_includes = repr(self.ignore_missing_includes)
        return f"SpecParser({sourcedir}, {macros}, {ignore_missing_includes})"

    @contextlib.contextmanager
    def _make_dummy_sources(self, sources: List[str]) -> Iterator[List[Path]]:
        """
        Context manager for creating temporary dummy sources to enable a spec file
        to be fully parsed by RPM.

        Args:
            sources: List of all sources (including patches) in a spec file.

        Yields:
            List of paths to each created dummy source.
        """
        # based on rpmFileIsCompressed() in rpmio/rpmfileutil.c in RPM source
        SIGNATURES = [
            (".bz2", b"BZh"),
            (".zip", b"PK00"),
            (".xz", b"\xfd\x37\x7a\x58\x5a\x00"),
            (".zst", b"\x28\xb5\x2f"),
            (".lz", b"LZIP"),
            (".lrz", b"LRZI"),
            (".gz", b"\x1f\x8b"),
            (".7z", b"7z\xbc\xaf\x27\x1c"),
        ]
        # number of bytes that RPM reads to determine the file type
        MAGIC_LENGTH = 13
        dummy_sources = []
        for source in sources:
            filename = get_filename_from_location(source)
            if not filename:
                continue
            path = self.sourcedir / filename
            if path.is_file():
                continue
            dummy_sources.append(path)
            for ext, magic in SIGNATURES:
                if filename.endswith(ext):
                    path.write_bytes(magic.ljust(MAGIC_LENGTH, b"\x00"))
                    break
            else:
                path.write_bytes(MAGIC_LENGTH * b"\x00")
        yield dummy_sources
        for path in dummy_sources:
            path.unlink()

    @contextlib.contextmanager
    def _sanitize_environment(self) -> Iterator[os._Environ]:
        """
        Context manager for sanitizing the environment for shell expansions.

        Temporarily sets LANG and LC_ALL to C.UTF-8 locale.

        Yields:
            Sanitized environment.
        """
        env = os.environ.copy()

        def restore(key):
            try:
                os.environ[key] = env[key]
            except KeyError:
                del os.environ[key]

        keys = ["LANG", "LC_ALL"]
        for key in keys:
            os.environ[key] = "C.UTF-8"
        try:
            yield os.environ
        finally:
            for key in keys:
                restore(key)

    def _do_parse(
        self, content: str, extra_macros: Optional[List[Tuple[str, str]]] = None
    ) -> Tuple[rpm.spec, bool]:
        """
        Parses the content of a spec file.

        Args:
            content: String representing the content of a spec file.
            extra_macros: List of extra macro definitions.

        Returns:
            Tuple of (parsed spec file as `rpm.spec` instance, indication whether
              at least one file to be included was ignored).

        Raises:
            RPMException, if parsing error occurs.
        """

        def get_rpm_spec(content, flags):
            Macros.reinit()
            for name, value in self.macros + (extra_macros or []):
                Macros.define(name, value)
            Macros.define("_sourcedir", str(self.sourcedir))
            with tempfile.NamedTemporaryFile() as tmp:
                tmp.write(content.encode())
                tmp.flush()
                try:
                    with self._sanitize_environment():
                        with capture_stderr() as stderr:
                            return rpm.spec(tmp.name, flags)
                except ValueError as e:
                    raise RPMException(stderr=stderr) from e

        def get_included_sources(content):
            include_regex = re.compile(r"^\s*%include\s+(.*)$")
            lines = content.splitlines()
            sources = []
            while lines:
                line = lines.pop(0)
                m = include_regex.match(line)
                if not m:
                    continue
                arg = m.group(1)
                while line.endswith("\\"):
                    line = lines.pop(0)
                    arg = arg[:-1] + line
                # we can expand macros here because the first non-build parse,
                # even though it failed, populated the macro context
                source = Path(Macros.expand(arg))
                # ignore files outside of sourcedir
                if source.parent.samefile(self.sourcedir):
                    sources.append(source.name)
            return sources

        tainted = False
        try:
            # do a non-build parse first, to get a list of sources
            spec = get_rpm_spec(content, rpm.RPMSPEC_ANYARCH | rpm.RPMSPEC_FORCE)
            sources = [s for s, _, _ in spec.sources]
        except RPMException:
            if self.ignore_missing_includes:
                sources = get_included_sources(content)
                if not sources:
                    # no point in trying again
                    raise
                with self._make_dummy_sources(sources) as dummy_sources:
                    if dummy_sources:
                        logger.warning(
                            "Created dummy sources for nonexistent includes:\n"
                            "\n".join(str(ds) for ds in dummy_sources)
                        )
                    # do a non-build parse again with dummy included sources
                    spec = get_rpm_spec(
                        content, rpm.RPMSPEC_ANYARCH | rpm.RPMSPEC_FORCE
                    )
                    sources = [s for s, _, _ in spec.sources]
                tainted = True
            else:
                raise

        # workaround RPM lua tables feature/bug
        #
        # RPM lua tables are a global storage that is used by lua macros and in turn
        # also by standard %sources and %patches macros
        #
        # they are initialized when a rpm.spec instance is created and destroyed
        # when a rpm.spec instance is deleted
        #
        # when a variable that holds a rpm.spec instance is assigned a new rpm.spec
        # instance, the old instance is garbage collected afterwards and that destroys
        # lua tables that were (re)initialized when the new instance was created
        #
        # explicitly deleting the old instance before creating a new one prevents this
        del spec

        with self._make_dummy_sources(sources):
            # do a full parse with dummy sources
            return get_rpm_spec(content, rpm.RPMSPEC_ANYARCH), tainted

    def parse(
        self, content: str, extra_macros: Optional[List[Tuple[str, str]]] = None
    ) -> None:
        """
        Parses the content of a spec file and updates the `spec` and `tainted` attributes.

        Args:
            content: String representing the content of a spec file.
            extra_macros: List of extra macro definitions.

        Raises:
            RPMException, if parsing error occurs.
        """
        if self.spec:
            # workaround RPM lua tables feature/bug, see above for details
            del self.spec
        self.spec, self.tainted = self._do_parse(content, extra_macros)
