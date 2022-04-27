# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import datetime
from typing import List, Optional, Union, overload

import arrow

from specfile.sections import Section
from specfile.types import SupportsIndex


class ChangelogEntry:
    """
    Class that represents a changelog entry.

    Attributes:
        header: Header of the entry.
        content: List of lines forming the content of the entry.
    """

    def __init__(
        self,
        header: str,
        content: List[str],
        following_lines: Optional[List[str]] = None,
    ) -> None:
        """
        Constructs a `ChangelogEntry` object.

        Args:
            header: Header of the entry.
            content: List of lines forming the content of the entry.
            following_lines: Extra lines that follow the entry.

        Returns:
            Constructed instance of `ChangelogEntry` class.
        """
        self.header = header
        self.content = content.copy()
        self._following_lines = (
            following_lines.copy() if following_lines is not None else []
        )

    def __str__(self) -> str:
        return f"{self.header}\n" + "\n".join(self.content) + "\n"

    def __repr__(self) -> str:
        content = repr(self.content)
        following_lines = repr(self._following_lines)
        return f"ChangelogEntry('{self.header}', {content}, {following_lines})"

    @property
    def extended_timestamp(self) -> bool:
        """Whether the timestamp present in the entry header is extended (date and time)."""
        try:
            arrow.get(self.header, "ddd MMM DD YYYY")
        except arrow.parser.ParserError:
            return True
        else:
            return False

    @staticmethod
    def assemble(
        timestamp: Union[datetime.date, datetime.datetime],
        author: str,
        content: List[str],
        evr: Optional[str] = None,
        append_newline: bool = True,
    ) -> "ChangelogEntry":
        """
        Assembles a changelog entry.

        Args:
            timestamp: Timestamp of the entry.
              Supply `datetime` rather than `date` for extended format.
            author: Author of the entry.
            content: List of lines forming the content of the entry.
            evr: EVR (epoch, version, release) of the entry.
            append_newline: Whether the entry should be followed by an empty line.

        Returns:
            Constructed instance of `ChangelogEntry` class.
        """
        header = "*"
        if isinstance(timestamp, datetime.datetime):
            # extended format
            header += arrow.Arrow.fromdatetime(timestamp).format(
                " ddd MMM DD hh:mm:ss ZZZ YYYY"
            )
        else:
            header += arrow.Arrow.fromdate(timestamp).format(" ddd MMM DD YYYY")
        header += f" {author}"
        if evr is not None:
            header += f" - {evr}"
        return ChangelogEntry(header, content, [""] if append_newline else None)


class Changelog(collections.UserList):
    """
    Class that represents a changelog.

    Attributes:
        data: List of individual entries.
    """

    def __init__(
        self,
        data: Optional[List[ChangelogEntry]] = None,
        predecessor: Optional[List[str]] = None,
    ) -> None:
        """
        Constructs a `Changelog` object.

        Args:
            data: List of individual changelog entries.
            predecessor: Lines at the beginning of a section that can't be parsed
              into changelog entries.

        Returns:
            Constructed instance of `Changelog` class.
        """
        super().__init__()
        if data is not None:
            self.data = data.copy()
        self._predecessor = predecessor.copy() if predecessor is not None else []

    def __str__(self) -> str:
        return "\n".join(str(i) for i in reversed(self.data))

    def __repr__(self) -> str:
        data = repr(self.data)
        predecessor = repr(self._predecessor)
        return f"Changelog({data}, {predecessor})"

    @overload
    def __getitem__(self, i: SupportsIndex) -> ChangelogEntry:
        pass

    @overload
    def __getitem__(self, i: slice) -> "Changelog":
        pass

    def __getitem__(self, i):
        if isinstance(i, slice):
            return Changelog(self.data[i], self._predecessor)
        else:
            return self.data[i]

    def __delitem__(self, i: Union[SupportsIndex, slice]) -> None:
        def delete(index):
            following_lines = self.data[index]._following_lines.copy()
            del self.data[index]
            if index < len(self.data):
                self.data[index]._following_lines.extend(following_lines[1:])
            else:
                self._predecessor.extend(following_lines[1:])

        if isinstance(i, slice):
            for index in reversed(range(len(self.data))[i]):
                delete(index)
        else:
            delete(i)

    @staticmethod
    def parse(section: Section) -> "Changelog":
        """
        Parses a %changelog section.

        Args:
            section: Section to parse.

        Returns:
            Constructed instance of `Changelog` class.
        """
        data: List[ChangelogEntry] = []
        predecessor = []
        header = None
        content: List[str] = []
        following_lines: List[str] = []
        for line in section:
            if line.startswith("*"):
                if header:
                    data.insert(0, ChangelogEntry(header, content, following_lines))
                header = line
                content = []
                following_lines = []
            elif header:
                if line.strip():
                    content.append(line)
                else:
                    following_lines.append(line)
            else:
                predecessor.append(line)
        if header:
            data.insert(0, ChangelogEntry(header, content, following_lines))
        return Changelog(data, predecessor)

    def get_raw_section_data(self) -> List[str]:
        """
        Reconstructs section data from changelog.

        Returns:
            List of lines forming the reconstructed section data.
        """
        result = self._predecessor
        for entry in reversed(self.data):
            result.append(entry.header)
            result.extend(entry.content)
            result.extend(entry._following_lines)
        return result
