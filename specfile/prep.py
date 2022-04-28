# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import re
from abc import ABC
from typing import Any, Dict, List, Optional, Union, cast, overload

from specfile.macro_options import MacroOptions
from specfile.sections import Section
from specfile.types import SupportsIndex


class PrepMacro(ABC):
    """
    Class that represents a %prep macro.

    Attributes:
        name: Literal name of the macro.
        options: Options of the macro.
    """

    CANONICAL_NAME: str
    OPTSTRING: str
    DEFAULTS: Dict[str, Union[bool, int, str]]

    def __init__(
        self,
        name: str,
        options: MacroOptions,
        delimiter: str,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
        preceding_lines: Optional[List[str]] = None,
    ) -> None:
        """
        Constructs a `PrepMacro` object.

        Args:
            name: Literal name of the macro.
            options: Options of the macro.
            delimiter: Delimiter separating name and option string.
            prefix: Characters preceding the macro on a line.
            suffix: Characters following the macro on a line.
            preceding_lines: Lines of the %prep section preceding the macro.

        Returns:
            Constructed instance of `PrepMacro` class.
        """
        self.name = name
        self.options = options
        self._delimiter = delimiter
        self._prefix = prefix or ""
        self._suffix = suffix or ""
        self._preceding_lines = (
            preceding_lines.copy() if preceding_lines is not None else []
        )

    def __repr__(self) -> str:
        options = repr(self.options)
        preceding_lines = repr(self._preceding_lines)
        # determine class name dynamically so that inherited classes
        # don't have to reimplement __repr__()
        return (
            f"{self.__class__.__name__}('{self.name}', {options}, "
            f"'{self._delimiter}', '{self._prefix}', '{self._suffix}', "
            f"{preceding_lines})"
        )

    def get_raw_data(self) -> List[str]:
        options = str(self.options)
        return self._preceding_lines + [
            f"{self._prefix}{self.name}{self._delimiter}{options}{self._suffix}"
        ]


class SetupMacro(PrepMacro):
    """Class that represents a %setup macro."""

    CANONICAL_NAME: str = "%setup"
    OPTSTRING: str = "a:b:cDn:Tq"
    DEFAULTS: Dict[str, Union[bool, int, str]] = {
        "n": "%{name}-%{version}",
    }


class PatchMacro(PrepMacro):
    """Class that represents a %patch macro."""

    CANONICAL_NAME: str = "%patch"
    OPTSTRING: str = "P:p:REb:z:F:d:o:Z"
    DEFAULTS: Dict[str, Union[bool, int, str]] = {}

    @property
    def number(self) -> int:
        """Number of the %patch macro."""
        if self.options.P is not None:
            return int(self.options.P)
        tokens = re.split(r"(\d+)", self.name, maxsplit=1)
        if len(tokens) > 1:
            return int(tokens[1])
        return 0

    @number.setter
    def number(self, value: int) -> None:
        if self.options.P is not None:
            self.options.P = value
            return
        self.name = f"{self.CANONICAL_NAME}{value}"


class AutosetupMacro(PrepMacro):
    """Class that represents an %autosetup macro."""

    CANONICAL_NAME: str = "%autosetup"
    OPTSTRING: str = "a:b:cDn:TvNS:p:"
    DEFAULTS: Dict[str, Union[bool, int, str]] = {
        "n": "%{name}-%{version}",
        "S": "patch",
    }


class AutopatchMacro(PrepMacro):
    """Class that represents an %autopatch macro."""

    CANONICAL_NAME: str = "%autopatch"
    OPTSTRING: str = "vp:m:M:"
    DEFAULTS: Dict[str, Union[bool, int, str]] = {}


class PrepMacros(collections.UserList):
    """
    Class that represents a list of %prep macros.

    Attributes:
        data: List of individual %prep macros.
    """

    def __init__(
        self,
        data: Optional[List[PrepMacro]] = None,
        remainder: Optional[List[str]] = None,
    ) -> None:
        """
        Constructs a `PrepMacros` object.

        Args:
            data: List of individual %prep macros.
            remainder: Leftover lines in the section.

        Returns:
            Constructed instance of `PrepMacros` class.
        """
        super().__init__()
        if data is not None:
            self.data = data.copy()
        self._remainder = remainder.copy() if remainder is not None else []

    def __repr__(self) -> str:
        data = repr(self.data)
        remainder = repr(self._remainder)
        return f"PrepMacros({data}, {remainder})"

    def __contains__(self, item: object) -> bool:
        if isinstance(item, type):
            return any(isinstance(m, item) for m in self.data)
        return any(
            m.name.startswith(item) if item == "%patch" else m.name == item
            for m in self.data
        )

    @overload
    def __getitem__(self, i: SupportsIndex) -> PrepMacro:
        pass

    @overload
    def __getitem__(self, i: slice) -> "PrepMacros":
        pass

    def __getitem__(self, i):
        if isinstance(i, slice):
            return PrepMacros(self.data[i], self._remainder)
        else:
            return self.data[i]

    def __delitem__(self, i: Union[SupportsIndex, slice]) -> None:
        def delete(index):
            preceding_lines = self.data[index]._preceding_lines.copy()
            del self.data[index]
            if index < len(self.data):
                self.data[index]._preceding_lines = (
                    preceding_lines + self.data[index]._preceding_lines
                )
            else:
                self._remainder = preceding_lines + self._remainder

        if isinstance(i, slice):
            for index in reversed(range(len(self.data))[i]):
                delete(index)
        else:
            delete(i)

    def __getattr__(self, name: str) -> PrepMacro:
        if not self.valid_prep_macro(name):
            return super().__getattribute__(name)
        try:
            return self.data[self.find(f"%{name}")]
        except ValueError:
            raise AttributeError(name)

    def __delattr__(self, name: str) -> None:
        if not self.valid_prep_macro(name):
            return super().__delattr__(name)
        try:
            self.__delitem__(self.find(f"%{name}"))
        except ValueError:
            raise AttributeError(name)

    @staticmethod
    def valid_prep_macro(name: str) -> bool:
        return name in ("setup", "autosetup", "autopatch") or name.startswith("patch")

    def copy(self) -> "PrepMacros":
        return PrepMacros(self.data, self._remainder)

    def find(self, name: str) -> int:
        for i, macro in enumerate(self.data):
            if macro.name == name:
                return i
        raise ValueError

    def get_raw_data(self) -> List[str]:
        result = []
        for macro in self.data:
            result.extend(macro.get_raw_data())
        result.extend(self._remainder)
        return result


class Prep(collections.abc.Container):
    """
    Class that represents a %prep section.

    Attributes:
        macros: List of individual %prep macros.
    """

    def __init__(self, macros: PrepMacros) -> None:
        self.macros = macros.copy()

    def __repr__(self) -> str:
        macros = repr(self.macros)
        return f"Prep({macros})"

    def __contains__(self, item: object) -> bool:
        return item in self.macros

    def __getattr__(self, name: str) -> PrepMacro:
        if not self.macros.valid_prep_macro(name):
            return super().__getattribute__(name)
        return getattr(self.macros, name)

    def __delattr__(self, name: str) -> None:
        if not self.macros.valid_prep_macro(name):
            return super().__delattr__(name)
        return delattr(self.macros, name)

    def add_patch_macro(self, number: int, **kwargs: Any) -> None:
        """
        Adds a new %patch macro with given number and options.

        Args:
            number: Macro number.
            P: The -P option (patch number).
            p: The -p option (strip number).
            R: The -R option (reverse).
            E: The -E option (remove empty files).
            b: The -b option (backup).
            z: The -z option (suffix).
            F: The -F option (fuzz factor).
            d: The -d option (working directory).
            o: The -o option (output file).
            Z: The -Z option (set UTC times).
        """
        options = MacroOptions([], PatchMacro.OPTSTRING, PatchMacro.DEFAULTS)
        for k, v in kwargs.items():
            setattr(options, k, v)
        macro = PatchMacro(PatchMacro.CANONICAL_NAME, options, " ")
        macro.number = number
        index, _ = min(
            ((i, m) for i, m in enumerate(self.macros) if isinstance(m, PatchMacro)),
            key=lambda im: abs(im[1].number - number),
            default=(len(self.macros), None),
        )
        if (
            index < len(self.macros)
            and cast(PatchMacro, self.macros[index]).number <= number
        ):
            index += 1
        self.macros.insert(index, macro)

    def remove_patch_macro(self, number: int) -> None:
        """
        Removes a %patch macro with given number.

        Args:
            number: Macro number.
        """
        index = next(
            (
                i
                for i, m in enumerate(self.macros)
                if isinstance(m, PatchMacro) and m.number == number
            ),
            None,
        )
        if index:
            del self.macros[index]

    @staticmethod
    def parse(section: Section) -> "Prep":
        """
        Parses a section into a `Prep` object.

        Args:
            section: %prep section.

        Returns:
            Constructed instance of `Prep` class.
        """
        # match also macros enclosed in conditionalized macro expansion
        # e.g.: %{?with_system_nss:%patch30 -p3 -b .nss_pkcs11_v3}
        macro_regex = re.compile(
            r"(?P<c>%{!?\?\w+:)?.*?"
            r"(?P<m>%(setup|patch\d*|autopatch|autosetup))"
            r"(?P<d>\s*)"
            r"(?P<o>.*?)"
            r"(?(c)}|$)"
        )
        data = []
        buffer: List[str] = []
        for line in section:
            m = macro_regex.search(line)
            if m:
                name, delimiter, option_string = (
                    m.group("m"),
                    m.group("d"),
                    m.group("o"),
                )
                prefix, suffix = line[: m.start("m")], line[m.end("o") :]
                cls = next(
                    (
                        cls
                        for cls in PrepMacro.__subclasses__()
                        if name.startswith(cls.CANONICAL_NAME)
                    ),
                    None,
                )
                if not cls:
                    buffer.append(line)
                    continue
                options = MacroOptions(
                    MacroOptions.tokenize(option_string), cls.OPTSTRING, cls.DEFAULTS
                )
                data.append(cls(name, options, delimiter, prefix, suffix, buffer))
                buffer = []
            else:
                buffer.append(line)
        return Prep(PrepMacros(data, buffer))

    def get_raw_section_data(self) -> List[str]:
        """
        Reconstructs section data from `Prep` object.

        Returns:
            List of lines forming the reconstructed section data.
        """
        return self.macros.get_raw_data()
