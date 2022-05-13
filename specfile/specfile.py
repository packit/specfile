# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import contextlib
import datetime
import re
import subprocess
import types
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Type, Union

import arrow

from specfile.changelog import Changelog, ChangelogEntry
from specfile.exceptions import SpecfileException
from specfile.prep import Prep
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
    def prep(self) -> Iterator[Optional[Prep]]:
        """
        Context manager for accessing %prep section.

        Yields:
            Spec file %prep section as `Prep` object.
        """
        with self.sections() as sections:
            try:
                section = sections.prep
            except AttributeError:
                yield None
            else:
                prep = Prep.parse(section)
                try:
                    yield prep
                finally:
                    section.data = prep.get_raw_section_data()

    @contextlib.contextmanager
    def sources(
        self,
        allow_duplicates: bool = False,
        default_to_implicit_numbering: bool = False,
        default_source_number_digits: int = 1,
    ) -> Iterator[Sources]:
        """
        Context manager for accessing sources.

        Args:
            allow_duplicates: Whether to allow duplicate entries when adding new sources.
            default_to_implicit_numbering: Use implicit numbering (no source numbers) by default.
            default_source_number_digits: Default number of digits in a source number.

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
                    default_to_implicit_numbering,
                    default_source_number_digits,
                )
            finally:
                for section, sourcelist in sourcelists:
                    section.data = sourcelist.get_raw_section_data()

    @contextlib.contextmanager
    def patches(
        self,
        allow_duplicates: bool = False,
        default_to_implicit_numbering: bool = False,
        default_source_number_digits: int = 1,
    ) -> Iterator[Patches]:
        """
        Context manager for accessing patches.

        Args:
            allow_duplicates: Whether to allow duplicate entries when adding new patches.
            default_to_implicit_numbering: Use implicit numbering (no source numbers) by default.
            default_source_number_digits: Default number of digits in a source number.

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
                    default_to_implicit_numbering,
                    default_source_number_digits,
                )
            finally:
                for section, patchlist in patchlists:
                    section.data = patchlist.get_raw_section_data()

    @property
    def has_autochangelog(self) -> bool:
        """Whether the spec file uses %autochangelog."""
        with self.sections() as sections:
            try:
                section = sections.changelog
            except AttributeError:
                return False
            changelog = [ln.strip() for ln in section if ln.strip()]
            return changelog == ["%autochangelog"]

    def add_changelog_entry(
        self,
        entry: Union[str, List[str]],
        author: Optional[str] = None,
        email: Optional[str] = None,
        timestamp: Optional[Union[datetime.date, datetime.datetime]] = None,
    ) -> None:
        """
        Adds a new %changelog entry. Does nothing if there is no %changelog section
        or if %autochangelog is being used.

        If not specified, author and e-mail will be determined using rpmdev-packager, if available.
        Timestamp, if not set, will be set to current time (in local timezone).

        Args:
            entry: Entry text or list of entry lines.
            author: Author of the entry.
            email: E-mail of the author.
            timestamp: Timestamp of the entry.
              Supply `datetime` rather than `date` for extended format.
        """
        if self.has_autochangelog:
            return
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
            changelog.append(
                ChangelogEntry.assemble(
                    timestamp, author, entry, evr, append_newline=bool(changelog)
                )
            )

    @property
    def version(self) -> str:
        """Version string as stored in the spec file."""
        with self.tags() as tags:
            return tags.version.value

    @version.setter
    def version(self, value: str) -> None:
        with self.tags() as tags:
            tags.version.value = value

    @property
    def expanded_version(self) -> str:
        """Version string with macros expanded."""
        with self.tags() as tags:
            return tags.version.expanded_value

    @staticmethod
    def _split_raw_release(
        raw_release: str,
    ) -> Tuple[str, Optional[str], Optional[int]]:
        """
        Splits raw release string into release, dist and minorbump parts.

        Args:
            raw_release: Raw release string.

        Returns:
            Tuple of (release, dist, minorbump).
        """
        tokens = re.split(r"(%(?P<m>\{\??)?dist(?(m)\}))(\.(\d+))?$", raw_release)
        if len(tokens) == 1:
            return tokens[0], None, None
        release, dist, _, _, minorbump, *_ = tokens
        return release, dist, int(minorbump) if minorbump else None

    @classmethod
    def _get_updated_release(cls, raw_release: str, release: str) -> str:
        """
        Returns the specified raw release string updated with the specified release.
        Minorbump, if there is one, is removed.

        Args:
            raw_release: Raw release string.
            release: New release.

        Returns:
            Updated raw release string.
        """
        dist = cls._split_raw_release(raw_release)[1] or ""
        return f"{release}{dist}"

    @property
    def release(self) -> str:
        """Release string without the dist suffix."""
        return self._split_raw_release(self.raw_release)[0]

    @release.setter
    def release(self, value: str) -> None:
        self.raw_release = self._get_updated_release(self.raw_release, value)

    @property
    def raw_release(self) -> str:
        """Release string as stored in the spec file."""
        with self.tags() as tags:
            return tags.release.value

    @raw_release.setter
    def raw_release(self, value: str) -> None:
        with self.tags() as tags:
            tags.release.value = value

    @property
    def expanded_release(self) -> str:
        """Release string without the dist suffix with macros expanded."""
        return self.expand(self.release)

    @property
    def expanded_raw_release(self) -> str:
        """Release string with macros expanded."""
        with self.tags() as tags:
            return tags.release.expanded_value

    def set_version_and_release(self, version: str, release: str = "1") -> None:
        """
        Sets both version and release at the same time.

        Args:
            version: Version string.
            release: Release string, defaults to '1'.
        """
        with self.tags() as tags:
            tags.version.value = version
            tags.release.value = self._get_updated_release(tags.release.value, release)
