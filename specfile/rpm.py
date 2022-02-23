# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import contextlib
import io
import os
import re
import sys
import tempfile
from enum import IntEnum
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import rpm

from specfile.exceptions import MacroRemovalException, RPMException

MAX_REMOVAL_RETRIES = 20


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


class Macro:
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


class RPM:
    @staticmethod
    def parse(
        content: str, sourcedir: Path, macros: Optional[List[Tuple[str, str]]] = None
    ) -> rpm.spec:
        """
        Parses the content of a spec file.

        Args:
            content: String representing the content of a spec file.
            sourcedir: Path to sources and patches.
            macros: List of macro definitions that will be applied before parsing.

        Returns:
            Parsed spec file as `rpm.spec` instance.

        Raises:
            RPMException, if parsing error occurs.
        """
        Macros.reinit()
        for name, value in macros or []:
            Macros.define(name, value)
        Macros.define("_sourcedir", str(sourcedir))
        with tempfile.NamedTemporaryFile() as spec:
            spec.write(content.encode())
            spec.flush()
            try:
                with capture_stderr() as stderr:
                    return rpm.spec(spec.name, rpm.RPMSPEC_ANYARCH)
            except ValueError as e:
                raise RPMException(stderr=stderr) from e
