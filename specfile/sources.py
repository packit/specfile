# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import re
import urllib.parse
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union, cast, overload

from specfile.exceptions import SpecfileException
from specfile.rpm import Macros
from specfile.sourcelist import Sourcelist, SourcelistEntry
from specfile.tags import Comments, Tag, Tags


class Source(ABC):
    """Class that represents a source."""

    @property  # type: ignore
    @abstractmethod
    def number(self) -> int:
        """Source number."""
        ...

    @property  # type: ignore
    @abstractmethod
    def location(self) -> str:
        """Literal location of the source as stored in the spec file."""
        ...

    @location.setter  # type: ignore
    @abstractmethod
    def location(self, value: str) -> None:
        ...

    @property  # type: ignore
    @abstractmethod
    def expanded_location(self) -> str:
        """Location of the source after expanding macros."""
        ...

    @property  # type: ignore
    @abstractmethod
    def filename(self) -> str:
        """Literal filename of the source."""
        ...

    @property
    def remote(self) -> bool:
        """Whether the source is remote (location is URL)."""
        url = urllib.parse.urlsplit(self.expanded_location)
        return all((url.scheme, url.netloc))

    @property  # type: ignore
    @abstractmethod
    def expanded_filename(self) -> str:
        """Filename of the source after expanding macros."""
        ...

    @property  # type: ignore
    @abstractmethod
    def comments(self) -> Comments:
        """List of comments associated with the source."""
        ...


class TagSource(Source):
    """Class that represents a source backed by a spec file tag."""

    def __init__(self, tag: Tag, number: Optional[int] = None) -> None:
        """
        Constructs a `TagSource` object.

        Args:
            tag: Tag that this source represents.
            number: Source number (in the case of implicit numbering).

        Returns:
            Constructed instance of `TagSource` class.
        """
        self._tag = tag
        self._number = number

    def __repr__(self) -> str:
        tag = repr(self._tag)
        return f"TagSource({tag}, {self._number})"

    def _extract_number(self) -> Optional[str]:
        """
        Extracts source number from tag name.

        Returns:
            Extracted number or None if there isn't one.
        """
        tokens = re.split(r"(\d+)", self._tag.name, maxsplit=1)
        if len(tokens) > 1:
            return tokens[1]
        return None

    @property
    def number(self) -> int:
        """Source number."""
        return self._number or int(self._extract_number() or 0)

    @property
    def number_digits(self) -> int:
        """Number of digits in the source number."""
        if self._number:
            return 0
        return len(self._extract_number() or "")

    @property
    def location(self) -> str:
        """Literal location of the source as stored in the spec file."""
        return self._tag.value

    @location.setter
    def location(self, value: str) -> None:
        self._tag.value = value

    @property
    def expanded_location(self) -> str:
        """Location of the source after expanding macros."""
        return self._tag.expanded_value

    @property
    def filename(self) -> str:
        """Literal filename of the source."""
        return Path(urllib.parse.urlsplit(self._tag.value).path).name

    @property
    def expanded_filename(self) -> str:
        """Filename of the source after expanding macros."""
        return Path(urllib.parse.urlsplit(self._tag.expanded_value).path).name

    @property
    def comments(self) -> Comments:
        """List of comments associated with the source."""
        return self._tag.comments


class ListSource(Source):
    """Class that represents a source backed by a line in a %sourcelist/%patchlist section."""

    def __init__(self, source: SourcelistEntry, number: int) -> None:
        """
        Constructs a `ListSource` object.

        Args:
            source: Sourcelist entry that this source represents.
            number: Source number.

        Returns:
            Constructed instance of `ListSource` class.
        """
        self._source = source
        self._number = number

    def __repr__(self) -> str:
        source = repr(self._source)
        return f"ListSource({source}, {self._number})"

    @property
    def number(self) -> int:
        """Source number."""
        return self._number

    @property
    def location(self) -> str:
        """Literal location of the source as stored in the spec file."""
        return self._source.location

    @location.setter
    def location(self, value: str) -> None:
        self._source.location = value

    @property
    def expanded_location(self) -> str:
        """Location of the source after expanding macros."""
        return self._source.expanded_location

    @property
    def filename(self) -> str:
        """Literal filename of the source."""
        return Path(urllib.parse.urlsplit(self._source.location).path).name

    @property
    def expanded_filename(self) -> str:
        """Filename of the source after expanding macros."""
        return Path(urllib.parse.urlsplit(self._source.expanded_location).path).name

    @property
    def comments(self) -> Comments:
        """List of comments associated with the source."""
        return self._source.comments


class Sources(collections.abc.MutableSequence):
    """Class that represents a sequence of all sources."""

    PREFIX: str = "Source"

    def __init__(
        self,
        tags: Tags,
        sourcelists: List[Sourcelist],
        allow_duplicates: bool = False,
        default_to_implicit_numbering: bool = False,
        default_source_number_digits: int = 1,
    ) -> None:
        """
        Constructs a `Sources` object.

        Args:
            tags: All spec file tags.
            sourcelists: List of all %sourcelist sections.
            allow_duplicates: Whether to allow duplicate entries when adding new sources.
            default_to_implicit_numbering: Use implicit numbering (no source numbers) by default.
            default_source_number_digits: Default number of digits in a source number.

        Returns:
            Constructed instance of `Sources` class.
        """
        self._tags = tags
        self._sourcelists = sourcelists
        self._allow_duplicates = allow_duplicates
        self._default_to_implicit_numbering = default_to_implicit_numbering
        self._default_source_number_digits = default_source_number_digits

    def __repr__(self) -> str:
        tags = repr(self._tags)
        sourcelists = repr(self._sourcelists)
        allow_duplicates = repr(self._allow_duplicates)
        default_to_implicit_numbering = repr(self._default_to_implicit_numbering)
        # determine class name dynamically so that inherited classes
        # don't have to reimplement __repr__()
        return (
            f"{self.__class__.__name__}({tags}, {sourcelists}, {allow_duplicates}, "
            f"{default_to_implicit_numbering}, {self._default_source_number_digits})"
        )

    def __contains__(self, location: object) -> bool:
        items = self._get_items()
        if not items:
            return False
        return location in [s.location for s in list(zip(*items))[0]]

    def __add__(
        self, other: Union[Source, Iterable[Source], "Sources"]
    ) -> List[Source]:
        if isinstance(other, Source):
            return list(self) + [other]
        return list(self) + list(other)

    def __len__(self) -> int:
        return len(self._get_items())

    @overload
    def __getitem__(self, i: int) -> Source:
        pass

    @overload
    def __getitem__(self, i: slice) -> List[Source]:
        pass

    def __getitem__(self, i):
        items = self._get_items()
        if isinstance(i, slice):
            return list(zip(*items[i]))[0]
        else:
            return items[i][0]

    @overload
    def __setitem__(self, i: int, item: str) -> None:
        pass

    @overload
    def __setitem__(self, i: slice, item: Iterable[str]) -> None:
        pass

    def __setitem__(self, i, item):
        items = self._get_items()
        if isinstance(i, slice):
            for i0, i1 in enumerate(range(len(items))[i]):
                items[i1][0].location = item[i0]
        else:
            items[i][0].location = item

    def __delitem__(self, i: Union[int, slice]) -> None:
        items = self._get_items()
        if isinstance(i, slice):
            for _, container, index in reversed(items[i]):
                del container[index]
        else:
            _, container, index = items[i]
            del container[index]

    def _get_tags(self) -> List[Tuple[TagSource, Tags, int]]:
        """
        Gets all tag sources.

        Returns:
            List of tuples in the form of (source, container, index),
            where source is an instance of `TagSource` representing a tag,
            container is the container the tag is part of and index
            is its index within that container.
        """
        result = []
        last_number = -1
        for i, tag in enumerate(self._tags):
            if tag.name.capitalize() == self.PREFIX.capitalize():
                last_number += 1
                ts = TagSource(tag, last_number)
            elif tag.name.capitalize().startswith(self.PREFIX.capitalize()):
                ts = TagSource(tag)
                last_number = ts.number
            else:
                continue
            result.append((ts, self._tags, i))
        return result

    def _get_items(self) -> List[Tuple[Source, Union[Tags, Sourcelist], int]]:
        """
        Gets all sources.

        Returns:
            List of tuples in the form of (source, container, index),
            where source is an instance of `TagSource` or `ListSource`
            representing a source, container is the container the source
            is part of and index is its index within that container.
        """
        result = cast(
            List[Tuple[Source, Union[Tags, Sourcelist], int]], self._get_tags()
        )
        last_number = result[-1][0].number if result else -1
        result.extend(
            (ListSource(sl[i], last_number + 1 + i), sl, i)
            for sl in self._sourcelists
            for i in range(len(sl))
        )
        return result

    def _detect_implicit_numbering(self) -> bool:
        """
        Tries to detect if implicit numbering is being used, i.e. Source/Patch
        tags don't have numbers.

        Returns:
            True if implicit numbering is being/should be used, False otherwise.
        """
        tags = self._get_tags()
        if any(t._number is None for t, _, _ in tags):
            return False
        if len(tags) <= 1:
            return self._default_to_implicit_numbering
        return True

    def _get_tag_format(self, reference: TagSource, number: int) -> Tuple[str, str]:
        """
        Determines name and separator of a new source tag based on
        a reference tag and the requested source number.

        The new name has the same number of digits as the reference
        and the length of the separator is adjusted accordingly.

        Args:
            reference: Reference tag source.
            number: Requested source number.

        Returns:
            Tuple in the form of (name, separator).
        """
        prefix = self.PREFIX.capitalize()
        if self._detect_implicit_numbering():
            suffix = ""
        else:
            suffix = f"{number:0{reference.number_digits}}"
        name = f"{prefix}{suffix}"
        diff = len(reference._tag.name) - len(name)
        if diff >= 0:
            return name, reference._tag._separator + " " * diff
        return name, reference._tag._separator[:diff] or ":"

    def _get_initial_tag_setup(self, number: int = 0) -> Tuple[int, str, str]:
        """
        Determines the initial placement, name and separator of
        a new source tag. The placement is expressed as an index
        in the list of all tags.

        Args:
            number: Initial source number, defaults to 0.

        Returns:
            Tuple in the form of (index, name, separator).
        """
        prefix = self.PREFIX.capitalize()
        if self._default_to_implicit_numbering:
            suffix = ""
        else:
            suffix = f"{number:0{self._default_source_number_digits}}"
        return len(self._tags) if self._tags else 0, f"{prefix}{suffix}", ": "

    def _deduplicate_tag_names(self) -> None:
        """Eliminates duplicate numbers in source tag names."""
        tags = self._get_tags()
        if not tags:
            return
        tag_sources = sorted(list(zip(*tags))[0], key=lambda ts: ts.number)
        for ts0, ts1 in zip(tag_sources, tag_sources[1:]):
            if ts1.number <= ts0.number:
                ts1._tag.name, ts1._tag._separator = self._get_tag_format(
                    ts0, ts0.number + 1
                )

    def insert(self, i: int, location: str) -> None:
        """
        Inserts a new source at a specified index.

        Args:
            i: Requested index.
            location: Location of the new source.

        Raises:
            SpecfileException if duplicates are disallowed and there
            already is a source with the same location.
        """
        if not self._allow_duplicates and location in self:
            raise SpecfileException(f"Source '{location}' already exists")
        items = self._get_items()
        if i > len(items):
            i = len(items)
        if items:
            if i == len(items):
                source, container, index = items[-1]
                index += 1
                number = source.number + 1
            else:
                source, container, index = items[i]
                number = source.number
            if isinstance(source, TagSource):
                name, separator = self._get_tag_format(source, number)
                container.insert(
                    index,
                    Tag(name, location, Macros.expand(location), separator, Comments()),
                )
                self._deduplicate_tag_names()
            else:
                container.insert(index, SourcelistEntry(location, Comments()))
        elif self._sourcelists:
            self._sourcelists[-1].append(SourcelistEntry(location, Comments()))
        else:
            index, name, separator = self._get_initial_tag_setup()
            self._tags.insert(
                index,
                Tag(name, location, Macros.expand(location), separator, Comments()),
            )

    def insert_numbered(self, number: int, location: str) -> int:
        """
        Inserts a new source with the specified number.

        Args:
            number: Number of the new source.
            location: Location of the new source.

        Returns:
            Index of the newly inserted source.

        Raises:
            SpecfileException if duplicates are disallowed and there
            already is a source with the same location.
        """
        if not self._allow_duplicates and location in self:
            raise SpecfileException(f"Source '{location}' already exists")
        tags = self._get_tags()
        if tags:
            # find the nearest source tag
            i, (source, _, index) = min(
                enumerate(tags), key=lambda t: abs(t[1][0].number - number)
            )
            if source.number < number:
                i += 1
                index += 1
            name, separator = self._get_tag_format(source, number)
        else:
            i = 0
            index, name, separator = self._get_initial_tag_setup(number)
        self._tags.insert(
            index, Tag(name, location, Macros.expand(location), separator, Comments())
        )
        self._deduplicate_tag_names()
        return i

    def remove(self, location: str) -> None:
        """
        Removes sources by location.

        Args:
            location: Location of the sources to be removed.
        """
        for source, container, index in reversed(self._get_items()):
            if source.location == location:
                del container[index]

    def count(self, location: str) -> int:
        """
        Counts sources by location.

        Args:
            location: Location of the sources to be counted.

        Returns:
            Number of sources with the specified location.
        """
        items = self._get_items()
        if not items:
            return 0
        return len([s for s in list(zip(*items))[0] if s.location == location])


class Patches(Sources):
    """Class that represents a sequence of all patches."""

    PREFIX: str = "Patch"

    def _get_initial_tag_setup(self, number: int = 0) -> Tuple[int, str, str]:
        """
        Determines the initial placement, name and separator of
        a new source tag. The placement is expressed as an index
        in the list of all tags.

        Args:
            number: Initial source number, defaults to 0.

        Returns:
            Tuple in the form of (index, name, separator).
        """
        try:
            index, source = [
                (i, TagSource(t))
                for i, t in enumerate(self._tags)
                if t.name.capitalize().startswith("Source")
            ][-1]
        except IndexError:
            return super()._get_initial_tag_setup(number)
        name, separator = self._get_tag_format(source, 0)
        return index + 1, name, separator
