# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import re
from typing import List, Optional, SupportsIndex, Tuple, Union, overload


class MacroDefinition:
    def __init__(
        self,
        name: str,
        body: str,
        is_global: bool,
        whitespace: Tuple[str, str, str, str],
        preceding_lines: Optional[List[str]] = None,
    ) -> None:
        self.name = name
        self.body = body
        self.is_global = is_global
        self._whitespace = whitespace
        self._preceding_lines = (
            preceding_lines.copy() if preceding_lines is not None else []
        )

    def __repr__(self) -> str:
        is_global = repr(self.is_global)
        whitespace = repr(self._whitespace)
        preceding_lines = repr(self._preceding_lines)
        return (
            f"MacroDefinition('{self.name}', '{self.body}', {is_global}, "
            f"{whitespace}, {preceding_lines})"
        )

    def __str__(self) -> str:
        ws = self._whitespace
        macro = "%global" if self.is_global else "%define"
        return f"{ws[0]}{macro}{ws[1]}{self.name}{ws[2]}{self.body}{ws[3]}"

    def get_raw_data(self) -> List[str]:
        result = self._preceding_lines.copy()
        ws = self._whitespace
        macro = "%global" if self.is_global else "%define"
        body = self.body.replace("\n", "\\\n").splitlines()
        if body:
            body[-1] += ws[3]
        else:
            body = [ws[3]]
        result.append(f"{ws[0]}{macro}{ws[1]}{self.name}{ws[2]}{body[0]}")
        result.extend(body[1:])
        return result


class MacroDefinitions(collections.UserList):
    """
    Class that represents all macro definitions.

    Attributes:
        data: List of individual macro definitions.
    """

    def __init__(
        self,
        data: Optional[List[MacroDefinition]] = None,
        remainder: Optional[List[str]] = None,
    ) -> None:
        """
        Constructs a `MacroDefinitions` object.

        Args:
            data: List of individual macro definitions.
            remainder: Leftover lines that can't be parsed into macro definitions.

        Returns:
            Constructed instance of `MacroDefinitions` class.
        """
        super().__init__()
        if data is not None:
            self.data = data.copy()
        self._remainder = remainder.copy() if remainder is not None else []

    def __repr__(self) -> str:
        data = repr(self.data)
        remainder = repr(self._remainder)
        return f"MacroDefinitions({data}, {remainder})"

    def __contains__(self, name: object) -> bool:
        try:
            # use parent's __getattribute__() so this method can be called from __getattr__()
            data = super().__getattribute__("data")
        except AttributeError:
            return False
        return any(md.name == name for md in data)

    def __getattr__(self, name: str) -> MacroDefinition:
        if name not in self:
            return super().__getattribute__(name)
        try:
            return self.get(name)
        except ValueError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Union[MacroDefinition, List[str]]) -> None:
        if name not in self:
            return super().__setattr__(name, value)
        try:
            if isinstance(value, MacroDefinition):
                self.data[self.find(name)] = value
            else:
                self.data[self.find(name)].body = value
        except ValueError:
            raise AttributeError(name)

    def __delattr__(self, name: str) -> None:
        if name not in self:
            return super().__getattribute__(name)
        try:
            del self.data[self.find(name)]
        except ValueError:
            raise AttributeError(name)

    @overload
    def __getitem__(self, i: SupportsIndex) -> MacroDefinition:
        pass

    @overload
    def __getitem__(self, i: slice) -> "MacroDefinitions":
        pass

    def __getitem__(self, i):
        if isinstance(i, slice):
            return MacroDefinitions(self.data[i], self._remainder)
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

    def copy(self) -> "MacroDefinitions":
        return MacroDefinitions(self.data, self._remainder)

    def get(self, name: str) -> MacroDefinition:
        return self.data[self.find(name)]

    def find(self, name: str) -> int:
        for i, macro_definition in enumerate(self.data):
            if macro_definition.name == name:
                return i
        raise ValueError

    @classmethod
    def parse(cls, lines: List[str]) -> "MacroDefinitions":
        """
        Parses given lines into macro defintions.

        Args:
            lines: Lines to parse.

        Returns:
            Constructed instance of `MacroDefinitions` class.
        """
        md_regex = re.compile(
            r"""
            ^
            (\s*)                 # optional preceding whitespace
            (%(?:global|define))  # scope-defining macro definition
            (\s+)
            (\w+(?:\(.*?\))?)     # macro name with optional arguments in parentheses
            (\s+)
            (.*?)                 # macro body
            (\s*|\\)              # optional following whitespace or a backslash indicating
                                  # that the macro body continues on the next line
            $
            """,
            re.VERBOSE,
        )
        data = []
        buffer: List[str] = []
        while lines:
            line = lines.pop(0)
            m = md_regex.match(line)
            if m:
                ws0, macro, ws1, name, ws2, body, ws3 = m.groups()
                if ws3 == "\\":
                    while line.endswith("\\") and lines:
                        line = lines.pop(0)
                        body += "\n" + line.rstrip("\\")
                    tokens = re.split(r"(\s+)$", body, maxsplit=1)
                    if len(tokens) == 1:
                        body = tokens[0]
                        ws3 = ""
                    else:
                        body, ws3, _ = tokens
                data.append(
                    MacroDefinition(
                        name, body, macro == "%global", (ws0, ws1, ws2, ws3), buffer
                    )
                )
                buffer = []
            else:
                buffer.append(line)
        return cls(data, buffer)

    def get_raw_data(self) -> List[str]:
        result = []
        for macro_definition in self.data:
            result.extend(macro_definition.get_raw_data())
        result.extend(self._remainder)
        return result
