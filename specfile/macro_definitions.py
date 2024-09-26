# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
import re
from enum import Enum, auto
from typing import TYPE_CHECKING, List, Optional, Tuple, Union, overload

from specfile.conditions import process_conditions
from specfile.formatter import formatted
from specfile.types import SupportsIndex
from specfile.utils import UserList, count_brackets

if TYPE_CHECKING:
    from specfile.specfile import Specfile


class CommentOutStyle(Enum):
    """Style of commenting out a macro definition."""

    DNL = auto()
    """Using the _%dnl_ macro."""

    HASH = auto()
    """Replacing _%_ in _%global_/_%define_ with _#_."""

    OTHER = auto()
    """Prepending the definition with _#_ followed by arbitrary string."""


class MacroDefinition:
    """
    Class that represents a macro definition. Macro definition starts with _%global_
    or _%define_ keyword, followed by macro name, optional argument string enclosed
    in parentheses and macro body.

    Attributes:
        name: Macro name.
        body: Macro body.
        is_global: Whether the macro is defined using _%global_ rather than _%define_.
        commented_out: Whether the definition is commented out.
        comment_out_style: Style of commenting out. See `CommentOutStyle`.
        valid: Whether the definition is not located in a false branch of a condition.
    """

    def __init__(
        self,
        name: str,
        body: str,
        is_global: bool,
        commented_out: bool,
        comment_out_style: CommentOutStyle,
        whitespace: Tuple[str, str, str, str],
        prefix: str = "",
        valid: bool = True,
        preceding_lines: Optional[List[str]] = None,
    ) -> None:
        """
        Initializes a macro definition object.

        Args:
            name: Macro name.
            body: Macro body.
            is_global: Whether the macro is defined using _%global_ rather than _%define_.
            commented_out: Whether the definition is commented out.
            comment_out_style: Style of commenting out. See `CommentOutStyle`.
            whitespace: Tuple of whitespace - (preceding the definition, preceding macro name,
                preceding macro body, following the body).
            prefix: String preceding the start of the definition.
            valid: Whether the definition is not located in a false branch of a condition.
            preceding_lines: Extra lines that precede the definition.
        """
        self.name = name
        self.body = body
        self.is_global = is_global
        self.commented_out = commented_out
        self.comment_out_style = comment_out_style
        self._whitespace = whitespace
        self._prefix = prefix
        self.valid = valid
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
            and self.commented_out == other.commented_out
            and self.comment_out_style == other.comment_out_style
            and self._whitespace == other._whitespace
            and self._prefix == other._prefix
            and self._preceding_lines == other._preceding_lines
        )

    @formatted
    def __repr__(self) -> str:
        return (
            f"MacroDefinition({self.name!r}, {self.body!r}, {self.is_global!r}, "
            f"{self.commented_out!r}, {self.comment_out_style!r}, {self._whitespace!r}, "
            f"{self._prefix!r}, {self.valid!r}, {self._preceding_lines!r})"
        )

    def __str__(self) -> str:
        ws = self._whitespace
        dnl = ""
        sc = "%"
        if self.commented_out:
            if self.comment_out_style is CommentOutStyle.DNL:
                dnl = "%dnl"
            elif self.comment_out_style is CommentOutStyle.HASH:
                sc = "#"
        macro = "global" if self.is_global else "define"
        return f"{ws[0]}{dnl}{self._prefix}{sc}{macro}{ws[1]}{self.name}{ws[2]}{self.body}{ws[3]}"

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
        dnl = ""
        sc = "%"
        if self.commented_out:
            if self.comment_out_style is CommentOutStyle.DNL:
                dnl = "%dnl"
            elif self.comment_out_style is CommentOutStyle.HASH:
                sc = "#"
        macro = "global" if self.is_global else "define"
        body = (self.body + ws[3]).split("\n")
        result.append(
            f"{ws[0]}{dnl}{self._prefix}{sc}{macro}{ws[1]}{self.name}{ws[2]}{body[0]}"
        )
        result.extend(body[1:])
        return result


class MacroDefinitions(UserList[MacroDefinition]):
    """
    Class that represents a list of all macro definitions.

    Attributes:
        data: List of individual macro definitions.
    """

    def __init__(
        self,
        data: Optional[List[MacroDefinition]] = None,
        remainder: Optional[List[str]] = None,
    ) -> None:
        """
        Initializes a macro definitions object.

        Args:
            data: List of individual macro definitions.
            remainder: Leftover lines that can't be parsed into macro definitions.
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

    def __setattr__(self, name: str, value: Union[MacroDefinition, str]) -> None:
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

    def get(self, name: str, position: Optional[int] = None) -> MacroDefinition:
        return self.data[self.find(name, position)]

    def find(self, name: str, position: Optional[int] = None) -> int:
        """
        Finds a macro definition with the specified name. If position is not specified,
        returns the first valid matching macro definiton. If there is no such macro
        definition, returns the first match, if any. If position is specified and there is
        a matching macro definition at that position, it is returned, otherwise
        `ValueError` is raised.

        Args:
            name: Name of the tag to find.
            position: Optional position in the spec file.

        Returns:
            Index of the matching tag.

        Raises:
            ValueError: If there is no match.
        """
        first_match = None
        for i, macro_definition in enumerate(self.data):
            if macro_definition.name == name:
                if position is None:
                    if first_match is None:
                        first_match = i
                    if macro_definition.valid:
                        return i
                elif macro_definition.get_position(self) == position:
                    return i
        if first_match is None or position is not None:
            raise ValueError
        return first_match

    @classmethod
    def _parse(
        cls, lines: Union[List[str], List[Tuple[str, bool]]]
    ) -> "MacroDefinitions":
        """
        Parses given lines into macro defintions.

        Args:
            lines: Lines to parse.

        Returns:
            New instance of `MacroDefinitions` class.
        """

        def pop(lines):
            line = lines.pop(0)
            if isinstance(line, str):
                return line, True
            else:
                return line

        md_regex = re.compile(
            r"""
            ^
            (\s*)                          # optional preceding whitespace
            (%dnl)?                        # optional DNL prefix
            ((?(2).*?%|(?:%|\#(?:.*?%)?))) # starting character with optional prefix
            (global|define)                # scope-defining macro definition
            (\s+)
            (\w+(?:\(.*?\))?)              # macro name with optional arguments in parentheses
            (\s+)
            (.*?)                          # macro body
            (\s*|\\)                       # optional following whitespace or a backslash indicating
                                           # that the macro body continues on the next line
            $
            """,
            re.VERBOSE,
        )
        data = []
        buffer: List[str] = []
        lines = lines.copy()
        while lines:
            line, valid = pop(lines)
            m = md_regex.match(line)
            if m:
                ws0, dnl, sc, macro, ws1, name, ws2, body, ws3 = m.groups()
                escaped = len(sc) > 1 and sc[-2:] == "%%"
                hashed = sc and sc[-1] == "#"
                if not dnl and not escaped and not hashed:
                    if ws3 == "\\":
                        body += ws3
                        ws3 = ""
                    bc, pc = count_brackets(body)
                    while (bc > 0 or pc > 0 or body.endswith("\\")) and lines:
                        line, _ = pop(lines)
                        body += "\n" + line
                        bc, pc = count_brackets(body)
                tokens = re.split(r"([^\S\n]+)$", body, maxsplit=1)
                if len(tokens) == 1:
                    body = tokens[0]
                else:
                    body, ws, _ = tokens
                    ws3 = ws + ws3
                data.append(
                    MacroDefinition(
                        name,
                        body,
                        macro == "global",
                        bool(dnl or hashed or escaped and "#" in sc),
                        (
                            CommentOutStyle.HASH
                            if hashed
                            else (
                                CommentOutStyle.OTHER
                                if escaped and "#" in sc
                                else CommentOutStyle.DNL
                            )
                        ),
                        (ws0, ws1, ws2, ws3),
                        sc[:-1] if len(sc) > 1 else "",
                        valid,
                        buffer,
                    )
                )
                buffer = []
            else:
                buffer.append(line)
        return cls(data, buffer)

    @classmethod
    def parse(
        cls,
        lines: List[str],
        with_conditions: bool = False,
        context: Optional["Specfile"] = None,
    ) -> "MacroDefinitions":
        """
        Parses given lines into macro defintions.

        Args:
            lines: Lines to parse.
            with_conditions: Whether to process conditions before parsing and populate
                the `valid` attribute.
            context: `Specfile` instance that defines the context for macro expansions.

        Returns:
            New instance of `MacroDefinitions` class.
        """
        result = cls._parse(lines)
        if not with_conditions:
            return result
        return cls._parse(process_conditions(lines, result, context))

    def get_raw_data(self) -> List[str]:
        result = []
        for macro_definition in self.data:
            result.extend(macro_definition.get_raw_data())
        result.extend(self._remainder)
        return result
