# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import datetime
from typing import List, Optional, Union

import arrow

from specfile.sections import Section


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
    ) -> None:
        self.header = header
        self.content = content.copy()

    def __str__(self) -> str:
        return f"{self.header}\n" + "\n".join(self.content) + "\n"

    def __repr__(self) -> str:
        content = repr(self.content)
        return f"ChangelogEntry('{self.header}', {content})"

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
    ) -> "ChangelogEntry":
        """
        Assembles a changelog entry.

        Args:
            timestamp: Timestamp of the entry.
              Supply `datetime` rather than `date` for extended format.
            author: Author of the entry.
            content: List of lines forming the content of the entry.
            evr: EVR (epoch, version, release) of the entry.

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
        return ChangelogEntry(header, content)


class Changelog(collections.UserList):
    """
    Class that represents a changelog.

    Attributes:
        data: List of individual entries.
    """

    def __str__(self) -> str:
        return "\n".join(str(i) for i in reversed(self.data))

    def __repr__(self) -> str:
        data = repr(self.data)
        return f"Changelog({data})"

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
        for line in section:
            if line.startswith("*"):
                data.insert(0, ChangelogEntry(line, content=[]))
            elif data and line:
                data[0].content.append(line)
        return Changelog(data)

    def get_raw_section_data(self) -> List[str]:
        """
        Reconstructs section data from changelog.

        Returns:
            List of lines forming the reconstructed section data.
        """
        result = []
        for entry in reversed(self.data):
            result.append(entry.header)
            result.extend(entry.content)
            result.append("")
        if result:
            # remove the last empty line
            result.pop()
        return result
