# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import copy
import re
from typing import TYPE_CHECKING, List, Optional, SupportsIndex, Union, cast, overload

from specfile.constants import SCRIPT_SECTIONS, SECTION_NAMES, SIMPLE_SCRIPT_SECTIONS
from specfile.formatter import formatted
from specfile.macros import Macros

if TYPE_CHECKING:
    from specfile.specfile import Specfile

# name for the implicit "preamble" section
PREAMBLE = "package"


class Section(collections.UserList):
    """
    Class that represents a spec file section.

    Attributes:
        id: ID of the section (name and optional arguments, without the leading '%').
        data: List of lines forming the content of the section, not including newline characters.
    """

    def __init__(
        self, id: str, data: Optional[List[str]] = None, separator: str = "\n"
    ) -> None:
        """
        Constructs a `Section` object.

        Args:
            id: ID of the section (name and optional arguments, without the leading '%').
            data: List of lines forming the content of the section,
              not including newline characters.
            separator: String separating section ID from its content, defaults to newline.

        Returns:
            Constructed instance of `Section` class.
        """
        super().__init__()
        if not id:
            raise ValueError("Section ID can't be empty")
        name = id.split()[0]
        if name.lower() not in SECTION_NAMES:
            raise ValueError(f"Invalid section name: '{name}'")
        self.id = id
        if data is not None:
            self.data = data.copy()
        self._separator = separator

    def __str__(self) -> str:
        data = "".join(f"{i}\n" for i in self.data)
        if self.id == PREAMBLE:
            return data
        return f"%{self.id}{self._separator}{data}"

    @formatted
    def __repr__(self) -> str:
        return f"Section({self.id!r}, {self.data!r}, {self._separator!r})"

    @overload
    def __getitem__(self, i: SupportsIndex) -> str:
        pass

    @overload
    def __getitem__(self, i: slice) -> "Section":
        pass

    def __getitem__(self, i):
        if isinstance(i, slice):
            return Section(self.id, self.data[i], self._separator)
        else:
            return self.data[i]

    @property
    def normalized_id(self) -> str:
        """Normalized ID of the section. All characters of name are lowercased."""
        tokens = re.split(r"(\s+)", self.id)
        if len(tokens) == 1:
            return tokens[0].lower()
        name, *rest = tokens
        return name.lower() + "".join(rest)

    @property
    def is_script(self) -> bool:
        """Whether the content of the section is a shell script."""
        normalized_name = self.normalized_id.split()[0]
        return normalized_name in SCRIPT_SECTIONS | SIMPLE_SCRIPT_SECTIONS

    def copy(self) -> "Section":
        return copy.copy(self)

    def get_raw_data(self) -> List[str]:
        if self.id == PREAMBLE:
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
                return context.expand(s)
            return Macros.expand(s)

        def split_content(line):
            # if the last token after macro expansion starts with a newline,
            # consider it part of section content
            tokens = re.split(r"(\s+)", line)
            if len(tokens) > 2:
                if expand(tokens[-1]).startswith("\n"):
                    return "".join(tokens[:-2]), [tokens[-1]], tokens[-2]
            return line, [], "\n"

        section_id_regexes = [
            re.compile(rf"^%{re.escape(n)}(\s+.*$|$)", re.IGNORECASE)
            for n in SECTION_NAMES
        ]
        section_starts = []
        for i, line in enumerate(lines):
            if line.startswith("%"):
                for r in section_id_regexes:
                    if r.match(line):
                        section_starts.append(i)
                        break
        section_starts.append(len(lines))
        data = [Section(PREAMBLE, lines[: section_starts[0]])]
        for start, end in zip(section_starts, section_starts[1:]):
            id, content, separator = split_content(lines[start][1:])
            data.append(Section(id, content + lines[start + 1 : end], separator))
        return cls(data)

    def get_raw_data(self) -> List[str]:
        result = []
        for section in self.data:
            result.extend(section.get_raw_data())
        return result
