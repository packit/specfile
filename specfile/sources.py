# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import copy
import re
import urllib.parse
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
    cast,
    overload,
)

from specfile.exceptions import DuplicateSourceException
from specfile.formatter import formatted
from specfile.macros import Macros
from specfile.sourcelist import Sourcelist, SourcelistEntry
from specfile.tags import Comments, Tag, Tags
from specfile.utils import get_filename_from_location

if TYPE_CHECKING:
    from specfile.specfile import Specfile


class Source(ABC):
    """Class that represents a source."""

    @property
    @abstractmethod
    def number(self) -> int:
        """Source number."""
        ...

    @property
    @abstractmethod
    def location(self) -> str:
        """Literal location of the source as stored in the spec file."""
        ...

    @location.setter
    def location(self, value: str) -> None:
        ...

    @property
    @abstractmethod
    def expanded_location(self) -> Optional[str]:
        """Location of the source after expanding macros."""
        ...

    @property
    @abstractmethod
    def filename(self) -> str:
        """Literal filename of the source."""
        ...

    @property
    def remote(self) -> bool:
        """Whether the source is remote (location is URL)."""
        url = urllib.parse.urlsplit(self.expanded_location)
        return all((url.scheme, url.netloc))

    @property
    @abstractmethod
    def expanded_filename(self) -> Optional[str]:
        """Filename of the source after expanding macros."""
        ...

    @property
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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TagSource):
            return NotImplemented
        return self._tag == other._tag and self._number == other._number

    @formatted
    def __repr__(self) -> str:
        # determine class name dynamically so that inherited classes
        # don't have to reimplement __repr__()
        return f"{self.__class__.__name__}({self._tag!r}, {self._number!r})"

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
        if self._number is not None:
            return self._number
        return int(self._extract_number() or 0)

    @property
    def number_digits(self) -> int:
        """
        Gets number of digits in the source number.

        Returns 0 if the source has no number, 1 if the source number
        has no leading zeros and the actual number of digits if there are
        any leading zeros.
        """
        if self._number is not None:
            return 0
        number = self._extract_number()
        if not number:
            return 0
        return len(number) if number.startswith("0") else 1

    @property
    def location(self) -> str:
        """Literal location of the source as stored in the spec file."""
        return self._tag.value

    @location.setter
    def location(self, value: str) -> None:
        self._tag.value = value

    @property
    def expanded_location(self) -> Optional[str]:
        """Location of the source after expanding macros."""
        return self._tag.expanded_value

    @property
    def filename(self) -> str:
        """Literal filename of the source."""
        return get_filename_from_location(self._tag.value)

    @property
    def expanded_filename(self) -> Optional[str]:
        """Filename of the source after expanding macros."""
        if self._tag.expanded_value is None:
            return None
        return get_filename_from_location(self._tag.expanded_value)

    @property
    def comments(self) -> Comments:
        """List of comments associated with the source."""
        return self._tag.comments


class ListSource(Source):
    """Class that represents a source backed by a line in a %sourcelist section."""

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ListSource):
            return NotImplemented
        return self._source == other._source and self._number == other._number

    @formatted
    def __repr__(self) -> str:
        # determine class name dynamically so that inherited classes
        # don't have to reimplement __repr__()
        return f"{self.__class__.__name__}({self._source!r}, {self._number!r})"

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
        return get_filename_from_location(self._source.location)

    @property
    def expanded_filename(self) -> str:
        """Filename of the source after expanding macros."""
        return get_filename_from_location(self._source.expanded_location)

    @property
    def comments(self) -> Comments:
        """List of comments associated with the source."""
        return self._source.comments


class Sources(collections.abc.MutableSequence):
    """Class that represents a sequence of all sources."""

    prefix: str = "Source"
    tag_class: type = TagSource
    list_class: type = ListSource

    def __init__(
        self,
        tags: Tags,
        sourcelists: List[Sourcelist],
        allow_duplicates: bool = False,
        default_to_implicit_numbering: bool = False,
        default_source_number_digits: int = 1,
        context: Optional["Specfile"] = None,
    ) -> None:
        """
        Constructs a `Sources` object.

        Args:
            tags: All spec file tags.
            sourcelists: List of all %sourcelist sections.
            allow_duplicates: Whether to allow duplicate entries when adding new sources.
            default_to_implicit_numbering: Use implicit numbering (no source numbers) by default.
            default_source_number_digits: Default number of digits in a source number.
            context: `Specfile` instance that defines the context for macro expansions.

        Returns:
            Constructed instance of `Sources` class.
        """
        self._tags = tags
        self._sourcelists = sourcelists
        self._allow_duplicates = allow_duplicates
        self._default_to_implicit_numbering = default_to_implicit_numbering
        self._default_source_number_digits = default_source_number_digits
        self._context = context

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sources):
            return NotImplemented
        return (
            self._tags == other._tags
            and self._sourcelists == other._sourcelists
            and self._allow_duplicates == other._allow_duplicates
            and self._default_to_implicit_numbering
            == other._default_to_implicit_numbering
            and self._default_source_number_digits
            == other._default_source_number_digits
        )

    @formatted
    def __repr__(self) -> str:
        # determine class name dynamically so that inherited classes
        # don't have to reimplement __repr__()
        return (
            f"{self.__class__.__name__}({self._tags!r}, {self._sourcelists!r}, "
            f"{self._allow_duplicates!r}, {self._default_to_implicit_numbering!r}, "
            f"{self._default_source_number_digits!r}, {self._context!r})"
        )

    def __deepcopy__(self, memo: Dict[int, Any]) -> "Sources":
        result = self.__class__.__new__(self.__class__)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "_context":
                continue
            setattr(result, k, copy.deepcopy(v, memo))
        result._context = self._context
        return result

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

    def _expand(self, s: str) -> str:
        if self._context:
            return self._context.expand(s)
        return Macros.expand(s)

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
            if tag.normalized_name == self.prefix:
                last_number += 1
                ts = self.tag_class(tag, last_number)
            elif tag.normalized_name.startswith(self.prefix):
                ts = self.tag_class(tag)
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
            (self.list_class(sl[i], last_number + 1 + i), sl, i)
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

    def _get_tag_format(
        self,
        reference: TagSource,
        number: int,
        number_digits_override: Optional[int] = None,
    ) -> Tuple[str, str]:
        """
        Determines name and separator of a new source tag based on
        a reference tag and the requested source number.

        The new name has the same number of digits as the reference
        (unless number_digits_override is set to a different value)
        and the length of the separator is adjusted accordingly.

        Args:
            reference: Reference tag source.
            number: Requested source number.
            number_digits_override: Requested number of digits in the source number.

        Returns:
            Tuple in the form of (name, separator).
        """
        if number_digits_override is not None:
            number_digits = number_digits_override
        else:
            number_digits = reference.number_digits
        if self._detect_implicit_numbering() or number_digits == 0:
            suffix = ""
        else:
            suffix = f"{number:0{number_digits}}"
        name = f"{self.prefix}{suffix}"
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
        if (
            self._default_to_implicit_numbering
            or self._default_source_number_digits == 0
        ):
            suffix = ""
        else:
            suffix = f"{number:0{self._default_source_number_digits}}"
        return len(self._tags) if self._tags else 0, f"{self.prefix}{suffix}", ": "

    def _deduplicate_tag_names(self, start: int = 0) -> None:
        """
        Eliminates duplicate numbers in source tag names.

        Args:
            start: Starting index, defaults to the first source tag.
        """
        tags = self._get_tags()
        if not tags:
            return
        tag_sources = list(zip(*tags[start:]))[0]
        for ts0, ts1 in zip(tag_sources, tag_sources[1:]):
            if ts1.number == ts0.number:
                if ts1._number is not None:
                    ts1._number = ts0.number + 1
                else:
                    ts1._tag.name, ts1._tag._separator = self._get_tag_format(
                        ts1, ts0.number + 1
                    )

    def insert(self, i: int, location: str) -> None:
        """
        Inserts a new source at a specified index.

        Args:
            i: Requested index.
            location: Location of the new source.

        Raises:
            DuplicateSourceException if duplicates are disallowed and there
              already is a source with the same location.
        """
        if not self._allow_duplicates and location in self:
            raise DuplicateSourceException(f"{self.prefix} '{location}' already exists")
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
            if isinstance(source, self.tag_class):
                name, separator = self._get_tag_format(cast(TagSource, source), number)
                container.insert(
                    index,
                    Tag(name, location, self._expand(location), separator, Comments()),
                )
                self._deduplicate_tag_names(i)
            else:
                container.insert(
                    index,
                    SourcelistEntry(location, Comments()),  # type: ignore[arg-type]
                )
        elif self._sourcelists:
            self._sourcelists[-1].append(SourcelistEntry(location, Comments()))
        else:
            index, name, separator = self._get_initial_tag_setup()
            self._tags.insert(
                index,
                Tag(name, location, self._expand(location), separator, Comments()),
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
            DuplicateSourceException if duplicates are disallowed and there
              already is a source with the same location.
        """
        if not self._allow_duplicates and location in self:
            raise DuplicateSourceException(f"{self.prefix} '{location}' already exists")
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
            index, Tag(name, location, self._expand(location), separator, Comments())
        )
        self._deduplicate_tag_names(i)
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

    def remove_numbered(self, number: int) -> None:
        """
        Removes a source by number.

        Args:
            number: Number of the source to be removed.
        """
        items = self._get_items()
        try:
            container, index = next((c, i) for s, c, i in items if s.number == number)
        except StopIteration:
            pass
        else:
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


class Patch(Source):
    """Class that represents a patch."""


class TagPatch(TagSource, Patch):
    """Class that represents a patch backed by a spec file tag."""


class ListPatch(ListSource, Patch):
    """Class that represents a patch backed by a line in a %patchlist section."""


class Patches(Sources):
    """Class that represents a sequence of all patches."""

    prefix: str = "Patch"
    tag_class: type = TagPatch
    list_class: type = ListPatch

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
                (i, Sources.tag_class(t))
                for i, t in enumerate(self._tags)
                if t.normalized_name.startswith(Sources.prefix)
            ][-1]
        except IndexError:
            return super()._get_initial_tag_setup(number)
        name, separator = self._get_tag_format(
            source, number, self._default_source_number_digits
        )
        return index + 1, name, separator
