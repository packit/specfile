# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import copy
import re
from typing import List, Optional, SupportsIndex, Tuple, Union, overload

from specfile.formatter import formatted


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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MacroDefinition):
            return NotImplemented
        return (
            self.name == other.name
            and self.body == other.body
            and self.is_global == other.is_global
            and self._whitespace == other._whitespace
            and self._preceding_lines == other._preceding_lines
        )

    @formatted
    def __repr__(self) -> str:
        return (
            f"MacroDefinition({self.name!r}, {self.body!r}, {self.is_global!r}, "
            f"{self._whitespace!r}, {self._preceding_lines!r})"
        )

    def __str__(self) -> str:
        ws = self._whitespace
        macro = "%global" if self.is_global else "%define"
        return f"{ws[0]}{macro}{ws[1]}{self.name}{ws[2]}{self.body}{ws[3]}"

    def get_position(self, container: "MacroDefinitions") -> int:
        """
        Gets position of this macro definition in the spec file.

        Args:
            container: `MacroDefinitions` instance that contains this macro definition.

        Returns:
            Position expressed as line number (starting from 0).
        """
        return sum(
            len(md.get_raw_data()) for md in container[: container.index(self)]
        ) + len(self._preceding_lines)

    def get_raw_data(self) -> List[str]:
        result = self._preceding_lines.copy()
        ws = self._whitespace
        macro = "%global" if self.is_global else "%define"
        body = self.body.splitlines()
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

    @formatted
    def __repr__(self) -> str:
        return f"MacroDefinitions({self.data!r}, {self._remainder!r})"

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
        return copy.copy(self)

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

        def count_brackets(s):
            bc = pc = 0
            chars = list(s)
            while chars:
                c = chars.pop(0)
                if c == "\\" and chars:
                    chars.pop(0)
                    continue
                if c == "%" and chars:
                    c = chars.pop(0)
                    if c == "{":
                        bc += 1
                    elif c == "(":
                        pc += 1
                    continue
                if c == "{" and bc > 0:
                    bc += 1
                    continue
                if c == "}" and bc > 0:
                    bc -= 1
                    continue
                if c == "(" and pc > 0:
                    pc += 1
                    continue
                if c == ")" and pc > 0:
                    pc -= 1
                    continue
            return bc, pc

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
        lines = lines.copy()
        while lines:
            line = lines.pop(0)
            m = md_regex.match(line)
            if m:
                ws0, macro, ws1, name, ws2, body, ws3 = m.groups()
                if ws3 == "\\":
                    body += ws3
                    ws3 = ""
                bc, pc = count_brackets(body)
                while (bc > 0 or pc > 0 or body.endswith("\\")) and lines:
                    line = lines.pop(0)
                    body += "\n" + line
                    bc, pc = count_brackets(body)
                tokens = re.split(r"(\s+)$", body, maxsplit=1)
                if len(tokens) == 1:
                    body = tokens[0]
                else:
                    body, ws, _ = tokens
                    ws3 = ws + ws3
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
