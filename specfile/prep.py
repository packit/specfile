# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import argparse
import collections
import re
import shlex
from abc import ABC, abstractmethod
from typing import List, Optional, overload

from specfile.sections import Section


class PrepMacro(ABC):
    """
    Class that represents a %prep macro.

    Attributes:
        name: Literal name of the macro.
    """

    CANONICAL_NAME: str

    def __init__(self, name: str, line: int) -> None:
        """
        Constructs a `PrepMacro` object.

        Args:
            name: Literal name of the macro.
            line: Line number in %prep section where the macro is located.

        Returns:
            Constructed instance of `PrepMacro` class.
        """
        self.name = name
        self._line = line
        self._options = argparse.Namespace()
        self._parser = argparse.ArgumentParser(add_help=False)
        self._setup_parser()

    def __repr__(self) -> str:
        # determine class name dynamically so that inherited classes
        # don't have to reimplement __repr__()
        return f"{self.__class__.__name__}('{self.name}', {self._line})"

    @abstractmethod
    def _setup_parser(self) -> None:
        """Configures internal `ArgumentParser` for the options of the macro."""
        ...

    def _parse_options(self, optstr: str) -> None:
        """
        Parses the given option string.

        Args:
            optstr: String representing options of the macro.
        """
        try:
            self._parser.parse_known_args(shlex.split(optstr), self._options)
        except SystemExit:
            # ignore errors
            pass

    @property
    def options(self) -> argparse.Namespace:
        """Options of the macro as `argparse.Namespace` instance."""
        return self._options


class SetupMacro(PrepMacro):
    """Class that represents a %setup macro."""

    CANONICAL_NAME: str = "%setup"

    def _setup_parser(self) -> None:
        """Configures internal `ArgumentParser` for the options of the macro."""
        self._parser.add_argument("-n", default="%{name}-%{version}")
        self._parser.add_argument("-q", action="store_true")
        self._parser.add_argument("-c", action="store_true")
        self._parser.add_argument("-D", action="store_true")
        self._parser.add_argument("-T", action="store_true")
        self._parser.add_argument("-b", type=int)
        self._parser.add_argument("-a", type=int)


class PatchMacro(PrepMacro):
    """Class that represents a %patch macro."""

    CANONICAL_NAME: str = "%patch"

    def _setup_parser(self) -> None:
        """Configures internal `ArgumentParser` for the options of the macro."""
        self._parser.add_argument("-P", type=int)
        self._parser.add_argument("-p", type=int)
        self._parser.add_argument("-b")
        self._parser.add_argument("-E", action="store_true")

    @property
    def index(self) -> int:
        """Numeric index of the %patch macro."""
        if self.options.P is not None:
            return self.options.P
        tokens = re.split(r"(\d+)", self.name, maxsplit=1)
        if len(tokens) > 1:
            return int(tokens[1])
        return 0


class AutosetupMacro(PrepMacro):
    """Class that represents an %autosetup macro."""

    CANONICAL_NAME: str = "%autosetup"

    def _setup_parser(self) -> None:
        """Configures internal `ArgumentParser` for the options of the macro."""
        self._parser.add_argument("-n", default="%{name}-%{version}")
        self._parser.add_argument("-v", action="store_true")
        self._parser.add_argument("-c", action="store_true")
        self._parser.add_argument("-D", action="store_true")
        self._parser.add_argument("-T", action="store_true")
        self._parser.add_argument("-b", type=int)
        self._parser.add_argument("-a", type=int)
        self._parser.add_argument("-N", action="store_true")
        self._parser.add_argument("-S", default="patch")
        self._parser.add_argument("-p", type=int)


class AutopatchMacro(PrepMacro):
    """Class that represents an %autopatch macro."""

    CANONICAL_NAME: str = "%autopatch"

    def _setup_parser(self) -> None:
        """Configures internal `ArgumentParser` for the options of the macro."""
        self._parser.add_argument("-v", action="store_true")
        self._parser.add_argument("-p", type=int)
        self._parser.add_argument("-m", type=int)
        self._parser.add_argument("-M", type=int)
        self._parser.add_argument("indices", type=int, nargs="*")


class PrepMacros(collections.abc.Sequence):
    """Class that represents a sequence of all %prep macros."""

    def __init__(self, section: Section) -> None:
        """
        Constructs a `PrepMacros` object.

        Args:
            section: %prep section.

        Returns:
            Constructed instance of `PrepMacros` class.
        """
        self._section = section

    def __repr__(self) -> str:
        section = repr(self._section)
        return f"PrepMacros({section})"

    def __contains__(self, item: object) -> bool:
        if isinstance(item, type):
            return any(isinstance(m, item) for m in self._get_items())
        elif isinstance(item, str):
            return any(m.CANONICAL_NAME == item for m in self._get_items())
        return False

    def __len__(self) -> int:
        return len(self._get_items())

    def _get_items(self) -> List[PrepMacro]:
        """
        Gets all supported %prep macros.

        Returns:
            List of instances of subclasses of PrepMacro.
        """
        comment_regex = re.compile(r"^\s*#.*$")
        # match also macros enclosed in conditionalized macro expansion
        # e.g.: %{?with_system_nss:%patch30 -p3 -b .nss_pkcs11_v3}
        macro_regex = re.compile(
            r"(?P<c>%{!?\?\w+:)?.*?"
            r"(?P<m>%(setup|patch\d*|autopatch|autosetup))\s*"
            r"(?P<o>.*?)(?(c)}|$)"
        )
        result: List[PrepMacro] = []
        for i, line in enumerate(self._section):
            if comment_regex.match(line):
                continue
            m = macro_regex.search(line)
            if not m:
                continue
            name, options = m.group("m"), m.group("o")
            macro: PrepMacro
            if name.startswith(PatchMacro.CANONICAL_NAME):
                macro = PatchMacro(name, i)
                macro._parse_options(options)
                # if %patch is indexed and has the -P option at the same time,
                # it's two macros in one
                if macro.options.P is not None and name != PatchMacro.CANONICAL_NAME:
                    macro.options.P = None
                    result.append(macro)
                    # add the second macro
                    macro = PatchMacro(PatchMacro.CANONICAL_NAME, i)
                    macro._parse_options(options)
                    result.append(macro)
                else:
                    result.append(macro)
            else:
                macro = next(
                    iter(
                        cls(name, i)  # type: ignore
                        for cls in PrepMacro.__subclasses__()
                        if cls.CANONICAL_NAME == name
                    ),
                    None,
                )
                if not macro:
                    continue
                macro._parse_options(options)
                result.append(macro)
        return result

    @overload
    def __getitem__(self, i: int) -> PrepMacro:
        pass

    @overload
    def __getitem__(self, i: slice) -> List[PrepMacro]:
        pass

    def __getitem__(self, i):
        return self._get_items()[i]


class Prep:
    """
    Class that represents a %prep section.

    Attributes:
        macros: Sequence of individual %prep macros.
            Recognized macros are %setup, %patch, %autosetup and %autopatch.
    """

    def __init__(self, section: Section) -> None:
        """
        Constructs a `Prep` object.

        Args:
            section: %prep section.

        Returns:
            Constructed instance of `Prep` class.
        """
        self._section = section
        self.macros = PrepMacros(self._section)

    def __repr__(self) -> str:
        section = repr(self._section)
        return f"Prep({section})"

    def add_patch_macro(
        self,
        index: int,
        P: Optional[int] = None,
        p: Optional[int] = None,
        b: Optional[str] = None,
        E: Optional[bool] = None,
    ) -> None:
        """
        Adds a new %patch macro with given index and options.

        If there are existing %patch macros, the new macro is added before,
        after or between them according to index. Otherwise it is added
        to the very end of %prep section.

        Beware that it is valid to specify non-zero index and the -P option
        at the same time, but the resulting macro behaves as two %patch macros
        (even if both indices are the same, in such case the patch is applied
        twice - you most likely don't want that).

        Also beware that there is no duplicity check, it is possible to add
        multiple %patch macros with the same index.

        Args:
            index: Numeric index of the macro.
            P: The -P option (patch index).
            p: The -p option (strip number).
            b: The -b option (backup).
            E: The -E option (remove empty files).
        """
        macro = f"%patch{index}"
        if P is not None:
            macro += f" -P{P}"
        if p is not None:
            macro += f" -p{p}"
        if b is not None:
            macro += f" -b {b}"
        if E:
            macro += " -E"
        macros = [m for m in self.macros if isinstance(m, PatchMacro)]
        if macros:
            lines = [
                m._line
                for m in sorted(macros, key=lambda m: m.index)
                if m.index < index
            ]
            if lines:
                self._section.insert(lines[-1] + 1, macro)
            else:
                self._section.insert(macros[0]._line, macro)
        else:
            self._section.append(macro)

    def remove_patch_macro(self, index: int) -> None:
        """
        Removes a %patch macro.

        If there are multiple %patch macros with the same index,
        all instances are removed.

        Note that this method always removes the entire line, even if
        for example the %patch macro is part of a conditionalized
        macro expansion.

        Args:
            index: Numeric index of the macro to remove.
        """
        lines = [
            m._line
            for m in self.macros
            if isinstance(m, PatchMacro) and m.index == index
        ]
        for line in reversed(lines):
            del self._section[line]
