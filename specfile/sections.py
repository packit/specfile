# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import copy
import re
from typing import TYPE_CHECKING, List, Optional, SupportsIndex, Union, cast, overload

from specfile.constants import (
    SCRIPT_SECTIONS,
    SECTION_NAMES,
    SECTION_OPTIONS,
    SIMPLE_SCRIPT_SECTIONS,
)
from specfile.formatter import formatted
from specfile.macro_definitions import MacroDefinitions
from specfile.macros import Macros
from specfile.options import Options

if TYPE_CHECKING:
    from specfile.specfile import Specfile

# name for the implicit "preamble" section
PREAMBLE = "package"


class Section(collections.UserList):
    """
    Class that represents a spec file section.

    Attributes:
        name: Name of the section (without the leading '%').
        options: Options of the section.
        data: List of lines forming the content of the section,
          not including newline characters.
    """

    def __init__(
        self,
        name: str,
        options: Optional[Options] = None,
        delimiter: str = "",
        separator: str = "\n",
        data: Optional[List[str]] = None,
    ) -> None:
        """
        Constructs a `Section` object.

        Args:
            name: Name of the section (without the leading '%').
            options: Options of the section.
            delimiter: Delimiter separating name and option string.
            separator: String separating name and options from section content,
              defaults to newline.
            data: List of lines forming the content of the section,
              not including newline characters.

        Returns:
            Constructed instance of `Section` class.
        """
        super().__init__()
        if name.lower() not in SECTION_NAMES:
            raise ValueError(f"Invalid section name: '{name}'")
        self.name = name
        self.options = (
            copy.deepcopy(options)
            if options is not None
            else Options([], SECTION_OPTIONS.get(name.lower()))
        )
        self._delimiter = delimiter
        self._separator = separator
        if data is not None:
            self.data = data.copy()

    def __str__(self) -> str:
        data = "".join(f"{i}\n" for i in self.data)
        if self.normalized_id == PREAMBLE:
            return data
        return f"%{self.id}{self._separator}{data}"

    @formatted
    def __repr__(self) -> str:
        return (
            f"Section({self.name!r}, {self.options!r}, {self._delimiter!r}, "
            f"{self._separator!r}, {self.data!r})"
        )

    @overload
    def __getitem__(self, i: SupportsIndex) -> str:
        pass

    @overload
    def __getitem__(self, i: slice) -> "Section":
        pass

    def __getitem__(self, i):
        if isinstance(i, slice):
            return Section(
                self.name, self.options, self._delimiter, self._separator, self.data[i]
            )
        else:
            return self.data[i]

    @property
    def normalized_name(self) -> str:
        """Normalized name of the section. All characters are lowercased."""
        return self.name.lower()

    @property
    def id(self) -> str:
        """ID of the section (name and options, without the leading '%')."""
        # ensure delimiter is not empty when there are any options
        if self.options and not self._delimiter:
            self._delimiter = " "
        return self.name + self._delimiter + str(self.options)

    @property
    def normalized_id(self) -> str:
        """Normalized ID of the section. All characters of name are lowercased."""
        # ensure delimiter is not empty when there are any options
        if self.options and not self._delimiter:
            self._delimiter = " "
        return self.normalized_name + self._delimiter + str(self.options)

    @property
    def is_script(self) -> bool:
        """Whether the content of the section is a shell script."""
        normalized_name = self.normalized_id.split()[0]
        return normalized_name in SCRIPT_SECTIONS | SIMPLE_SCRIPT_SECTIONS

    def copy(self) -> "Section":
        return copy.copy(self)

    def get_raw_data(self) -> List[str]:
        if self.normalized_id == PREAMBLE:
            return self.data
        return str(self).splitlines()


class Sections(collections.UserList):
    """
    Class that represents all spec file sections, hence the entire spec file.

    Sections can be accessed by index or conveniently by id as attributes:
    ```
    # print the third line of the first section
    print(sections[0][2])

    # remove the last line of %prep section
    del sections.prep[-1]

    # replace the entire %prep section
    sections.prep = ['line 1', 'line 2']

    # delete %changelog
    del sections.changelog
    ```

    Attributes:
        data: List of individual sections. Preamble is expected to always be the first.
    """

    def __str__(self) -> str:
        return "".join(str(i) for i in self.data)

    @formatted
    def __repr__(self) -> str:
        return f"Sections({self.data!r})"

    def __contains__(self, id: object) -> bool:
        try:
            # use parent's __getattribute__() so this method can be called from __getattr__()
            data = super().__getattribute__("data")
        except AttributeError:
            return False
        return any(s.normalized_id == cast(str, id).lower() for s in data)

    def __getattr__(self, id: str) -> Section:
        if id not in self:
            return super().__getattribute__(id)
        try:
            return self.get(id)
        except ValueError:
            raise AttributeError(id)

    def __setattr__(self, id: str, value: Union[Section, List[str]]) -> None:
        if id not in self:
            return super().__setattr__(id, value)
        try:
            if isinstance(value, Section):
                self.data[self.find(id)] = value
            else:
                self.data[self.find(id)].data = value
        except ValueError:
            raise AttributeError(id)

    def __delattr__(self, id: str) -> None:
        if id not in self:
            return super().__delattr__(id)
        try:
            del self.data[self.find(id)]
        except ValueError:
            raise AttributeError(id)

    def copy(self) -> "Sections":
        return copy.copy(self)

    def get(self, id: str) -> Section:
        return self.data[self.find(id)]

    def find(self, id: str) -> int:
        for i, section in enumerate(self.data):
            if section.normalized_id == id.lower():
                return i
        raise ValueError

    @classmethod
    def parse(
        cls, lines: List[str], context: Optional["Specfile"] = None
    ) -> "Sections":
        """
        Parses given lines into sections.

        Args:
            lines: Lines to parse.
            context: `Specfile` instance that defines the context for macro expansions.

        Returns:
            Constructed instance of `Sections` class.
        """

        def expand(s):
            if context:
                result = context.expand(
                    s, skip_parsing=getattr(expand, "skip_parsing", False)
                )
                # parse only once
                expand.skip_parsing = True
                return result
            return Macros.expand(s)

        def split_id(line):
            content = []
            separator = "\n"
            tokens = re.split(r"(\s+)", line)
            if len(tokens) > 2:
                # if the last token after macro expansion starts with a newline,
                # consider it part of section content
                if expand(tokens[-1]).startswith("\n"):
                    content = [tokens.pop()]
                    separator = tokens.pop()
            if len(tokens) > 2:
                name = tokens[0]
                delimiter = tokens[1]
                options = Options(
                    Options.tokenize("".join(tokens[2:])),
                    SECTION_OPTIONS.get(name.lower()),
                )
                return name, options, delimiter, separator, content
            return tokens[0], None, "", separator, content

        excluded_lines = []
        macro_definitions = MacroDefinitions.parse(lines)
        for md in macro_definitions:
            position = md.get_position(macro_definitions)
            excluded_lines.append(range(position, position + len(md.get_raw_data())))
        section_id_regexes = [
            re.compile(rf"^%{re.escape(n)}(\s+.*(?<!\\)$|$)", re.IGNORECASE)
            for n in SECTION_NAMES
        ]
        section_starts = []
        for i, line in enumerate(lines):
            # section can not start inside macro definition body
            if any(i in r for r in excluded_lines):
                continue
            if line.startswith("%"):
                for r in section_id_regexes:
                    if r.match(line):
                        section_starts.append(i)
                        break
        section_starts.append(len(lines))
        data = [Section(PREAMBLE, data=lines[: section_starts[0]])]
        for start, end in zip(section_starts, section_starts[1:]):
            name, options, delimiter, separator, content = split_id(lines[start][1:])
            data.append(
                Section(
                    name,
                    options,
                    delimiter,
                    separator,
                    content + lines[start + 1 : end],
                )
            )
        return cls(data)

    def get_raw_data(self) -> List[str]:
        result = []
        for section in self.data:
            result.extend(section.get_raw_data())
        return result
