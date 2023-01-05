# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import copy
import itertools
import re
from typing import Any, Iterable, List, Optional, SupportsIndex, Union, cast, overload

from specfile.constants import TAG_NAMES, TAGS_WITH_ARG
from specfile.formatter import formatted
from specfile.sections import Section
from specfile.utils import split_conditional_macro_expansion


def get_tag_name_regex(name: str) -> str:
    """Contructs regex corresponding to the specified tag name."""
    regex = re.escape(name)
    if name in TAGS_WITH_ARG:
        regex += r"(?:\s*\(\s*[^\s)]*\s*\))?"
    elif name in ["source", "patch"]:
        regex += r"\d*"
    return regex


class Comment:
    """
    Class that represents a comment.

    Attributes:
        text: Text of the comment.
        prefix: Comment prefix (hash character usually surrounded by some amount of whitespace).
    """

    def __init__(self, text: str, prefix: str = "# ") -> None:
        self.text = text
        self.prefix = prefix

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Comment):
            return NotImplemented
        return self.text == other.text and self.prefix == other.prefix

    def __str__(self) -> str:
        return f"{self.prefix}{self.text}"

    @formatted
    def __repr__(self) -> str:
        return f"Comment({self.text!r}, {self.prefix!r})"


class Comments(collections.UserList):
    """
    Class that represents comments associated with a tag, that is consecutive comment lines
    located directly above a tag definition.

    Attributes:
        data: List of individual comments.
    """

    def __init__(
        self,
        data: Optional[List[Comment]] = None,
        preceding_lines: Optional[List[str]] = None,
    ) -> None:
        """
        Constructs a `Comments` object.

        Args:
            data: List of individual comments.
            preceding_lines: Extra lines that precede comments associated with a tag.

        Returns:
            Constructed instance of `Comments` class.
        """
        super().__init__()
        if data is not None:
            self.data = data.copy()
        self._preceding_lines = (
            preceding_lines.copy() if preceding_lines is not None else []
        )

    @formatted
    def __repr__(self) -> str:
        return f"Comments({self.data!r}, {self._preceding_lines!r})"

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            return item in [c.text for c in self.data]
        return item in self.data

    @property
    def raw(self) -> List[str]:
        """List of comment texts"""
        return [c.text for c in self.data]

    @overload
    def __getitem__(self, i: SupportsIndex) -> Comment:
        pass

    @overload
    def __getitem__(self, i: slice) -> "Comments":
        pass

    def __getitem__(self, i):
        if isinstance(i, slice):
            return Comments(self.data[i], self._preceding_lines)
        else:
            return self.data[i]

    @overload
    def __setitem__(self, i: SupportsIndex, item: Union[Comment, str]) -> None:
        pass

    @overload
    def __setitem__(
        self, i: slice, item: Union[Iterable[Comment], Iterable[str]]
    ) -> None:
        pass

    def __setitem__(self, i, item):
        if isinstance(i, slice):
            for i0, i1 in enumerate(range(len(self.data))[i]):
                if isinstance(item[i0], str):
                    self.data[i1].text = item[i0]
                else:
                    self.data[i1] = item[i0]
        else:
            if isinstance(item, str):
                self.data[i].text = item
            else:
                self.data[i] = item

    def copy(self) -> "Comments":
        return copy.copy(self)

    def append(self, item: Union[Comment, str]) -> None:
        if isinstance(item, str):
            item = Comment(item)
        self.data.append(item)

    def insert(self, i: int, item: Union[Comment, str]) -> None:
        if isinstance(item, str):
            item = Comment(item)
        self.data.insert(i, item)

    def index(self, item: Union[Comment, str], *args: Any) -> int:
        if isinstance(item, str):
            return [c.text for c in self.data].index(item, *args)
        return self.data.index(item, *args)

    def extend(self, other: Union[Iterable[Comment], Iterable[str]]) -> None:
        for item in other:
            if isinstance(item, str):
                item = Comment(item)
            self.data.append(item)

    @classmethod
    def parse(cls, lines: List[str]) -> "Comments":
        """
        Parses list of lines into comments.

        Args:
            lines: List of lines that precede a tag definition.

        Returns:
            Constructed instance of `Comments` class.
        """
        comment_regex = re.compile(r"^(\s*#\s*)(.*)$")
        comments: List[Comment] = []
        preceding_lines: List[str] = []
        for line in reversed(lines):
            m = comment_regex.match(line)
            if not m or preceding_lines:
                preceding_lines.insert(0, line)
                continue
            comments.insert(0, Comment(*reversed(m.groups())))
        return cls(comments, preceding_lines)

    def get_raw_data(self) -> List[str]:
        return self._preceding_lines + [str(i) for i in self.data]


class Tag:
    """
    Class that represents a spec file tag.

    Attributes:
        name: Name of the tag.
        value: Literal value of the tag as stored in the spec file.
        comments: List of comments associated with the tag.
    """

    def __init__(
        self,
        name: str,
        value: str,
        expanded_value: Optional[str],
        separator: str,
        comments: Comments,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
    ) -> None:
        """
        Constructs a `Tag` object.

        Args:
            name: Name of the tag.
            value: Literal value of the tag as stored in the spec file.
            expanded_value: Value of the tag after expansion by RPM.
            separator:
              Separator between name and literal value (colon usually surrounded by some
              amount of whitespace).
            comments: List of comments associated with the tag.
            prefix: Characters preceding the tag on a line.
            suffix: Characters following the tag on a line.

        Returns:
            Constructed instance of `Tag` class.
        """
        name_regexes = [
            re.compile(get_tag_name_regex(t), re.IGNORECASE) for t in TAG_NAMES
        ]
        if not name or not any(r.match(name) for r in name_regexes):
            raise ValueError(f"Invalid tag name: '{name}'")
        self.name = name
        self.value = value
        self._expanded_value = expanded_value
        self._separator = separator
        self.comments = comments.copy()
        self._prefix = prefix or ""
        self._suffix = suffix or ""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tag):
            return NotImplemented
        return (
            self.name == other.name
            and self.value == other.value
            and self._expanded_value == other._expanded_value
            and self._separator == other._separator
            and self.comments == other.comments
            and self._prefix == other._prefix
            and self._suffix == other._suffix
        )

    @formatted
    def __repr__(self) -> str:
        return (
            f"Tag({self.name!r}, {self.value!r}, {self._expanded_value!r}, "
            f"{self._separator!r}, {self.comments!r}, {self._prefix!r}, {self._suffix!r})"
        )

    @property
    def normalized_name(self) -> str:
        """
        Normalized name of the tag. The first character is capitalized
        and the rest lowercased.
        """
        return self.name.capitalize()

    @property
    def valid(self) -> bool:
        """Validity of the tag. A tag is valid if it 'survives' the expansion of the spec file."""
        return self._expanded_value is not None

    @property
    def expanded_value(self) -> Optional[str]:
        """Value of the tag after expanding macros and evaluating all conditions."""
        return self._expanded_value

    def get_position(self, container: "Tags") -> int:
        """
        Gets position of this tag in a section.

        Args:
            container: `Tags` instance that contains this tag.

        Returns:
            Position expressed as line number (starting from 0).
        """
        return sum(
            len(t.comments.get_raw_data()) + 1
            for t in container[: container.index(self)]
        ) + len(self.comments.get_raw_data())


class Tags(collections.UserList):
    """
    Class that represents all tags in a certain %package section.

    Tags can be accessed by index or conveniently by name as attributes:
    ```
    # print name of the first tag
    print(tags[0].name)

    # set value of Url tag
    tags.url = 'https://example.com'

    # remove Source1 tag
    del tags.source1
    ```

    Attributes:
        data: List of individual tags.
    """

    def __init__(
        self, data: Optional[List[Tag]] = None, remainder: Optional[List[str]] = None
    ) -> None:
        """
        Constructs a `Tags` object.

        Args:
            data: List of individual tags.
            remainder: Leftover lines in a section that can't be parsed into tags.

        Returns:
            Constructed instance of `Tags` class.
        """
        super().__init__()
        if data is not None:
            self.data = data.copy()
        self._remainder = remainder.copy() if remainder is not None else []

    @formatted
    def __repr__(self) -> str:
        return f"Tags({self.data!r}, {self._remainder!r})"

    @overload
    def __getitem__(self, i: SupportsIndex) -> Tag:
        pass

    @overload
    def __getitem__(self, i: slice) -> "Tags":
        pass

    def __getitem__(self, i):
        if isinstance(i, slice):
            return Tags(self.data[i], self._remainder)
        else:
            return self.data[i]

    def __delitem__(self, i: Union[SupportsIndex, slice]) -> None:
        def delete(index):
            preceding_lines = self.data[index].comments._preceding_lines[:]
            del self.data[index]
            # preserve preceding lines of the deleted tag but compress empty lines
            if index < len(self.data):
                lines = self.data[index].comments._preceding_lines
            else:
                lines = self._remainder
            delimiter = []
            if preceding_lines and not preceding_lines[-1] or lines and not lines[0]:
                delimiter.append("")
            lines[:] = (
                list(
                    reversed(
                        list(
                            itertools.dropwhile(
                                lambda l: not l, reversed(preceding_lines)
                            )
                        )
                    )
                )
                + delimiter
                + list(itertools.dropwhile(lambda l: not l, lines))
            )

        if isinstance(i, slice):
            for index in reversed(range(len(self.data))[i]):
                delete(index)
        else:
            delete(i)

    def __contains__(self, name: object) -> bool:
        try:
            # use parent's __getattribute__() so this method can be called from __getattr__()
            data = super().__getattribute__("data")
        except AttributeError:
            return False
        return any(t.name.lower() == cast(str, name).lower() for t in data)

    def __getattr__(self, name: str) -> Tag:
        if name not in self:
            return super().__getattribute__(name)
        try:
            return self.data[self.find(name)]
        except ValueError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Union[Tag, str]) -> None:
        if name not in self:
            return super().__setattr__(name, value)
        try:
            if isinstance(value, Tag):
                self.data[self.find(name)] = value
            else:
                self.data[self.find(name)].value = value
        except ValueError:
            raise AttributeError(name)

    def __delattr__(self, name: str) -> None:
        if name not in self:
            return super().__delattr__(name)
        try:
            del self.data[self.find(name)]
        except ValueError:
            raise AttributeError(name)

    def copy(self) -> "Tags":
        return copy.copy(self)

    def find(self, name: str) -> int:
        for i, tag in enumerate(self.data):
            if tag.name.capitalize() == name.capitalize():
                return i
        raise ValueError

    def insert(self, i: int, item: Tag) -> None:
        if i > len(self.data):
            i = len(self.data)
        if i < len(self.data):
            lines = self.data[i].comments._preceding_lines
        else:
            lines = self._remainder
        self.data.insert(i, item)
        # do not make the new tag part of a condition block (in case there is one)
        index = next(
            (i for i, line in enumerate(lines) if line.startswith("%endif")), -1
        )
        if index >= 0:
            item.comments._preceding_lines[0:0] = lines[: index + 1]
            del lines[: index + 1]

    @classmethod
    def parse(
        cls, raw_section: Section, parsed_section: Optional[Section] = None
    ) -> "Tags":
        """
        Parses a section into tags.

        Args:
            raw_section: Raw (unprocessed) section.
            parsed_section: The same section after parsing.

        Returns:
            Constructed instance of `Tags` class.
        """

        def regex_pattern(tag):
            name_regex = get_tag_name_regex(tag)
            return rf"^(?P<n>{name_regex})(?P<s>\s*:\s*)(?P<v>.+)"

        tag_regexes = [re.compile(regex_pattern(t), re.IGNORECASE) for t in TAG_NAMES]
        data = []
        buffer: List[str] = []
        for line in raw_section:
            line, prefix, suffix = split_conditional_macro_expansion(line)
            # find out if there is a match for one of the tag regexes
            m = next((m for m in (r.match(line) for r in tag_regexes) if m), None)
            if m:
                # find out if any line in the parsed section matches the same regex
                tag_regex = re.compile(regex_pattern(m.group("n")))
                e = next(
                    (
                        e
                        for e in (tag_regex.match(pl) for pl in parsed_section or [])
                        if e
                    ),
                    None,
                )
                expanded_value = e.group("v") if e else None
                data.append(
                    Tag(
                        m.group("n"),
                        m.group("v"),
                        expanded_value,
                        m.group("s"),
                        Comments.parse(buffer),
                        prefix,
                        suffix,
                    )
                )
                buffer = []
            else:
                buffer.append(line)
        return cls(data, buffer)

    def get_raw_section_data(self) -> List[str]:
        """
        Reconstructs section data from tags.

        Returns:
            List of lines forming the reconstructed section data.
        """
        result = []
        for tag in self.data:
            result.extend(tag.comments.get_raw_data())
            result.append(
                f"{tag._prefix}{tag.name}{tag._separator}{tag.value}{tag._suffix}"
            )
        result.extend(self._remainder)
        return result
