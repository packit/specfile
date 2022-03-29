# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import contextlib
import datetime
import subprocess
import types
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Type, Union

import arrow

from specfile.changelog import Changelog, ChangelogEntry
from specfile.exceptions import SpecfileException
from specfile.rpm import RPM, Macros
from specfile.sections import Sections
from specfile.sourcelist import Sourcelist
from specfile.sources import Patches, Sources
from specfile.tags import Tags


class Specfile:
    """
    Class that represents a spec file.

    Attributes:
        path: Path to the spec file.
        sourcedir: Path to sources and patches.
        autosave: Whether to automatically save any changes made.
        macros: List of extra macro definitions.
    """

    def __init__(
        self,
        path: Union[Path, str],
        sourcedir: Optional[Union[Path, str]] = None,
        autosave: bool = False,
        macros: Optional[List[Tuple[str, str]]] = None,
    ) -> None:
        self.path = Path(path)
        self.sourcedir = Path(sourcedir or self.path.parent)
        self.autosave = autosave
        self.macros = macros.copy() if macros is not None else []
        self._sections = Sections.parse(self.path.read_text())
        self._spec = RPM.parse(str(self._sections), self.sourcedir, self.macros)
        self._parsed_sections = Sections.parse(self._spec.parsed)

    def __enter__(self) -> "Specfile":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[types.TracebackType],
    ) -> None:
        self.save()

    def reload(self) -> None:
        """Reload the spec file content."""
        self._sections = Sections.parse(self.path.read_text())
        self._spec = RPM.parse(str(self._sections), self.sourcedir, self.macros)
        self._parsed_sections = Sections.parse(self._spec.parsed)

    def save(self) -> None:
        """Save the spec file content."""
        self.path.write_text(str(self._sections))

    def expand(
        self, expression: str, extra_macros: Optional[List[Tuple[str, str]]] = None
    ) -> str:
        """
        Expands an expression in the context of the spec file.

        Args:
            expression: Expression to expand.
            extra_macros: Extra macros to be defined before expansion is performed.

        Returns:
            Expanded expression.
        """
        RPM.parse(
            str(self._sections), self.sourcedir, self.macros + (extra_macros or [])
        )
        return Macros.expand(expression)

    @contextlib.contextmanager
    def sections(self) -> Iterator[Sections]:
        """
        Context manager for accessing spec file sections.

        Yields:
            Spec file sections as `Sections` object.
        """
        yield self._sections
        self._spec = RPM.parse(str(self._sections), self.sourcedir, self.macros)
        self._parsed_sections = Sections.parse(self._spec.parsed)
        if self.autosave:
            self.save()

    @contextlib.contextmanager
    def tags(self, section: str = "package") -> Iterator[Tags]:
        """
        Context manager for accessing tags in a specified section.

        Args:
            section: Name of the requested section. Defaults to preamble.

        Yields:
            Tags in the section as `Tags` object.
        """
        with self.sections() as sections:
            raw_section = getattr(sections, section)
            parsed_section = getattr(self._parsed_sections, section, None)
            tags = Tags.parse(raw_section, parsed_section)
            try:
                yield tags
            finally:
                raw_section.data = tags.get_raw_section_data()

    @contextlib.contextmanager
    def changelog(self) -> Iterator[Optional[Changelog]]:
        """
        Context manager for accessing changelog.

        Yields:
            Spec file changelog as `Changelog` object or None if there is no %changelog section.
        """
        with self.sections() as sections:
            try:
                section = sections.changelog
            except AttributeError:
                yield None
            else:
                changelog = Changelog.parse(section)
                try:
                    yield changelog
                finally:
                    section.data = changelog.get_raw_section_data()

    @contextlib.contextmanager
    def sources(self, allow_duplicates: bool = False) -> Iterator[Sources]:
        """
        Context manager for accessing sources.

        Args:
            allow_duplicates: Whether to allow duplicate entries when adding new sources.

        Yields:
            Spec file sources as `Sources` object.
        """
        with self.sections() as sections, self.tags() as tags:
            sourcelists = [
                (s, Sourcelist.parse(s)) for s in sections if s.name == "sourcelist"
            ]
            try:
                yield Sources(
                    tags,
                    list(zip(*sourcelists))[1] if sourcelists else [],
                    allow_duplicates,
                )
            finally:
                for section, sourcelist in sourcelists:
                    section.data = sourcelist.get_raw_section_data()

    @contextlib.contextmanager
    def patches(self, allow_duplicates: bool = False) -> Iterator[Patches]:
        """
        Context manager for accessing patches.

        Args:
            allow_duplicates: Whether to allow duplicate entries when adding new patches.

        Yields:
            Spec file patches as `Patches` object.
        """
        with self.sections() as sections, self.tags() as tags:
            patchlists = [
                (s, Sourcelist.parse(s)) for s in sections if s.name == "patchlist"
            ]
            try:
                yield Patches(
                    tags,
                    list(zip(*patchlists))[1] if patchlists else [],
                    allow_duplicates,
                )
            finally:
                for section, patchlist in patchlists:
                    section.data = patchlist.get_raw_section_data()

    def add_changelog_entry(
        self,
        entry: Union[str, List[str]],
        author: Optional[str] = None,
        email: Optional[str] = None,
        timestamp: Optional[Union[datetime.date, datetime.datetime]] = None,
    ) -> None:
        """
        Adds a new %changelog entry. Does nothing if there is no %changelog section.

        If not specified, author and e-mail will be determined using rpmdev-packager, if available.
        Timestamp, if not set, will be set to current time (in local timezone).

        Args:
            entry: Entry text or list of entry lines.
            author: Author of the entry.
            email: E-mail of the author.
            timestamp: Timestamp of the entry.
              Supply `datetime` rather than `date` for extended format.
        """
        with self.changelog() as changelog:
            if changelog is None:
                return
            evr = self.expand(
                "%{?epoch:%{epoch}:}%{version}-%{release}", extra_macros=[("dist", "")]
            )
            if isinstance(entry, str):
                entry = [entry]
            if timestamp is None:
                now = arrow.now()
                # honor the timestamp format, but default to date-only
                if changelog and changelog[-1].extended_timestamp:
                    timestamp = now.datetime
                else:
                    timestamp = now.date()
            if author is None:
                try:
                    author = subprocess.check_output("rpmdev-packager").decode().strip()
                except (FileNotFoundError, subprocess.CalledProcessError) as e:
                    raise SpecfileException("Failed to auto-detect author") from e
            elif email is not None:
                author += f" <{email}>"
            changelog.append(ChangelogEntry.assemble(timestamp, author, entry, evr))
