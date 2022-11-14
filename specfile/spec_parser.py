# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import contextlib
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import rpm

from specfile.exceptions import RPMException
from specfile.macros import Macros
from specfile.utils import capture_stderr, get_filename_from_location

logger = logging.getLogger(__name__)


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
