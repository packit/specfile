# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, overload

from specfile.conditions import process_conditions
from specfile.formatter import formatted
from specfile.macro_definitions import MacroDefinitions
from specfile.macros import Macros
from specfile.sections import Section
from specfile.tags import Comments
from specfile.types import SupportsIndex
from specfile.utils import UserList

if TYPE_CHECKING:
    from specfile.specfile import Specfile


class SourcelistEntry:
    """
    Class that represents a spec file source/patch in a _%sourcelist_/_%patchlist_.

    Attributes:
        location: Literal location of the source/patch as stored in the spec file.
        comments: List of comments associated with the source/patch.
        valid: Whether the entry is not located in a false branch of a condition.
    """

    def __init__(
        self,
        location: str,
        comments: Comments,
        valid: bool = True,
        context: Optional["Specfile"] = None,
    ) -> None:
        """
        Initializes a sourcelist entry object.

        Args:
            location: Literal location of the source/patch as stored in the spec file.
            comments: List of comments associated with the source/patch.
            valid: Whether the entry is not located in a false branch of a condition.
            context: `Specfile` instance that defines the context for macro expansions.
        """
        self.location = location
        self.comments = comments.copy()
        self.valid = valid
        self._context = context

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SourcelistEntry):
            return NotImplemented
        return self.location == other.location and self.comments == other.comments

    @formatted
    def __repr__(self) -> str:
        return (
            f"SourcelistEntry({self.location!r}, {self.comments!r}, "
            f"{self.valid!r}, {self._context!r})"
        )

    def __deepcopy__(self, memo: Dict[int, Any]) -> "SourcelistEntry":
        result = self.__class__.__new__(self.__class__)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "_context":
                continue
            setattr(result, k, copy.deepcopy(v, memo))
        result._context = self._context
        return result

    @property
    def expanded_location(self) -> str:
        """URL of the source/patch after expanding macros."""
        if self._context:
            return self._context.expand(self.location)
        return Macros.expand(self.location)


class Sourcelist(UserList[SourcelistEntry]):
    """
    Class that represents entries in a _%sourcelist_/_%patchlist_ section.

    Attributes:
        data: List of individual sources/patches.
    """

    def __init__(
        self,
        data: Optional[List[SourcelistEntry]] = None,
        remainder: Optional[List[str]] = None,
    ) -> None:
        """
        Initializes a sourcelist object.

        Args:
            data: List of individual sources/patches.
            remainder: Leftover lines in a section that can't be parsed into sources/patches.
        """
        super().__init__()
        if data is not None:
            self.data = data.copy()
        self._remainder = remainder.copy() if remainder is not None else []

    @formatted
    def __repr__(self) -> str:
        return f"Sourcelist({self.data!r}, {self._remainder!r})"

    @overload
    def __getitem__(self, i: SupportsIndex) -> SourcelistEntry:
        pass

    @overload
    def __getitem__(self, i: slice) -> "Sourcelist":
        pass

    def __getitem__(self, i):
        if isinstance(i, slice):
            return Sourcelist(self.data[i], self._remainder)
        else:
            return self.data[i]

    def copy(self) -> "Sourcelist":
        return copy.copy(self)

    @classmethod
    def parse(
        cls, section: Section, context: Optional["Specfile"] = None
    ) -> "Sourcelist":
        """
        Parses a section into sources/patches.

        Args:
            section: _%sourcelist_/_%patchlist_ section.
            context: `Specfile` instance that defines the context for macro expansions.

        Returns:
            New instance of `Sourcelist` class.
        """
        macro_definitions = MacroDefinitions.parse(list(section))
        lines = process_conditions(list(section), macro_definitions, context)
        data = []
        buffer: List[str] = []
        for line, valid in lines:
            if line and not line.lstrip().startswith("#"):
                data.append(
                    SourcelistEntry(line, Comments.parse(buffer), valid, context)
                )
                buffer = []
            else:
                buffer.append(line)
        return cls(data, buffer)

    def get_raw_section_data(self) -> List[str]:
        """
        Reconstructs section data from sources/patches.

        Returns:
            List of lines forming the reconstructed section data.
        """
        result = []
        for source in self.data:
            result.extend(source.comments.get_raw_data())
            result.append(source.location)
        result.extend(self._remainder)
        return result
