# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import contextlib
import datetime
import re
import subprocess
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Type, Union

from specfile.changelog import Changelog, ChangelogEntry
from specfile.exceptions import SourceNumberException, SpecfileException
from specfile.macro_definitions import MacroDefinition, MacroDefinitions
from specfile.prep import Prep
from specfile.rpm import RPM, Macros
from specfile.sections import Section, Sections
from specfile.sourcelist import Sourcelist
from specfile.sources import Patches, Sources
from specfile.tags import Tag, Tags
from specfile.value_parser import SUBSTITUTION_GROUP_PREFIX, ValueParser


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
        self._lines = self.path.read_text().splitlines()
        self._spec = RPM.parse(str(self), self.sourcedir, self.macros)

    def __repr__(self) -> str:
        path = repr(self.path)
        sourcedir = repr(self.sourcedir)
        autosave = repr(self.autosave)
        macros = repr(self.macros)
        return f"Specfile({path}, {sourcedir}, {autosave}, {macros})"

    def __str__(self) -> str:
        return "\n".join(self._lines) + "\n"

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
        self._lines = self.path.read_text().splitlines()
        self._spec = RPM.parse(str(self), self.sourcedir, self.macros)

    def save(self) -> None:
        """Save the spec file content."""
        self.path.write_text(str(self))

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
        RPM.parse(str(self), self.sourcedir, self.macros + (extra_macros or []))
        return Macros.expand(expression)

    @contextlib.contextmanager
    def lines(self) -> Iterator[List[str]]:
        """
        Context manager for accessing spec file lines.

        Yields:
            Spec file lines as list of strings.
        """
        try:
            yield self._lines
        finally:
            self._spec = RPM.parse(str(self), self.sourcedir, self.macros)
            if self.autosave:
                self.save()

    @contextlib.contextmanager
    def macro_definitions(self) -> Iterator[MacroDefinitions]:
        """
        Context manager for accessing macro definitions.

        Yields:
            Macro definitions in the spec file as `MacroDefinitions` object.
        """
        with self.lines() as lines:
            macro_definitions = MacroDefinitions.parse(lines)
            try:
                yield macro_definitions
            finally:
                lines[:] = macro_definitions.get_raw_data()

    @contextlib.contextmanager
    def sections(self) -> Iterator[Sections]:
        """
        Context manager for accessing spec file sections.

        Yields:
            Spec file sections as `Sections` object.
        """
        with self.lines() as lines:
            sections = Sections.parse(lines)
            try:
                yield sections
            finally:
                lines[:] = sections.get_raw_data()

    @property
    def parsed_sections(self) -> Sections:
        """Parsed spec file sections."""
        return Sections.parse(self._spec.parsed.splitlines())

    @contextlib.contextmanager
    def tags(self, section: Union[str, Section] = "package") -> Iterator[Tags]:
        """
        Context manager for accessing tags in a specified section.

        Args:
            section: Name of the requested section or an existing `Section` instance.
              Defaults to preamble.

        Yields:
            Tags in the section as `Tags` object.
        """
        if isinstance(section, Section):
            raw_section = section
            parsed_section = getattr(self.parsed_sections, section.name, None)
            tags = Tags.parse(raw_section, parsed_section)
            try:
                yield tags
            finally:
                raw_section.data = tags.get_raw_section_data()
        else:
            with self.sections() as sections:
                raw_section = getattr(sections, section)
                parsed_section = getattr(self.parsed_sections, section, None)
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
        with self.sections() as sections, self.tags(sections.package) as tags:
            sourcelists = [
                (s, Sourcelist.parse(s, context=self))
                for s in sections
                if s.name == "sourcelist"
            ]
            try:
                yield Sources(
                    tags,
                    list(zip(*sourcelists))[1] if sourcelists else [],
                    allow_duplicates,
                    default_to_implicit_numbering,
                    default_source_number_digits,
                    context=self,
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
        with self.sections() as sections, self.tags(sections.package) as tags:
            patchlists = [
                (s, Sourcelist.parse(s, context=self))
                for s in sections
                if s.name == "patchlist"
            ]
            try:
                yield Patches(
                    tags,
                    list(zip(*patchlists))[1] if patchlists else [],
                    allow_duplicates,
                    default_to_implicit_numbering,
                    default_source_number_digits,
                    context=self,
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
                # honor the timestamp format, but default to date-only
                if changelog and changelog[-1].extended_timestamp:
                    timestamp = datetime.datetime.now().astimezone()
                else:
                    timestamp = datetime.date.today()
            if author is None:
                try:
                    author = subprocess.check_output("rpmdev-packager").decode().strip()
                except (FileNotFoundError, subprocess.CalledProcessError) as e:
                    raise SpecfileException("Failed to auto-detect author") from e
            elif email is not None:
                author += f" <{email}>"
            if changelog:
                # try to preserve padding of day of month
                padding = max(
                    (e.day_of_month_padding for e in reversed(changelog)), key=len
                )
            else:
                padding = "0"
            changelog.append(
                ChangelogEntry.assemble(
                    timestamp,
                    author,
                    entry,
                    evr,
                    day_of_month_padding=padding,
                    append_newline=bool(changelog),
                )
            )

    def _tag(name: str, doc: str) -> property:  # type: ignore[misc]
        """
        Returns a property that allows to get/set value of a specified tag.

        Args:
            name: Tag name.
            doc: Property docstring.

        Returns:
            Tag value property.
        """

        def getter(self) -> Optional[str]:
            with self.tags() as tags:
                try:
                    return getattr(tags, name).value
                except AttributeError:
                    return None

        def setter(self, value: str) -> None:
            with self.tags() as tags:
                getattr(tags, name).value = value

        return property(getter, setter, doc=doc)

    def _expanded_tag(name: str, doc: str) -> property:  # type: ignore[misc]
        """
        Returns a property that allows to get expanded value of a specified tag.

        Args:
            name: Tag name.
            doc: Property docstring.

        Returns:
            Expanded tag value property.
        """

        def getter(self) -> Optional[str]:
            with self.tags() as tags:
                try:
                    return getattr(tags, name).expanded_value
                except AttributeError:
                    return None

        return property(getter, doc=doc)

    name = _tag("name", "Name as stored in the spec file.")
    expanded_name = _expanded_tag("name", "Name with macros expanded.")

    version = _tag("version", "Version as stored in the spec file.")
    expanded_version = _expanded_tag("version", "Version with macros expanded.")

    raw_release = _tag("release", "Release string as stored in the spec file.")
    expanded_raw_release = _expanded_tag(
        "release", "Release string with macros expanded."
    )

    summary = _tag("summary", "Summary as stored in the spec file.")
    expanded_summary = _expanded_tag("summary", "Summary with macros expanded.")

    license = _tag("license", "License as stored in the spec file.")
    expanded_license = _expanded_tag("license", "License with macros expanded.")

    url = _tag("url", "URL as stored in the spec file.")
    expanded_url = _expanded_tag("url", "URL with macros expanded.")

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
    def expanded_release(self) -> str:
        """Release string without the dist suffix with macros expanded."""
        return self.expand(self.release)

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

    def add_patch(
        self,
        location: str,
        number: Optional[int] = None,
        comment: Optional[str] = None,
        initial_number: int = 0,
        number_digits: int = 4,
    ) -> None:
        """
        Adds a patch.

        Args:
            location: Patch location (filename or URL).
            number: Patch number. It will be auto-assigned if not specified.
              If specified, it must be higher than any existing patch number.
            comment: Associated comment.
            initial_number: Auto-assigned number to start with if there are no patches.
            number_digits: Number of digits in the patch number.

        Raises:
            SourceNumberException when the specified patch number is not higher
              than any existing patch number.
        """
        with self.patches(default_source_number_digits=number_digits) as patches:
            highest_number = max((p.number for p in patches), default=-1)
            if number is not None:
                if number <= highest_number:
                    raise SourceNumberException(
                        "Patch number must be higher than any existing patch number"
                    )
            else:
                number = max(highest_number + 1, initial_number)
            index = patches.insert_numbered(number, location)
            if comment:
                patches[index].comments.extend(comment.splitlines())

    def update_value(
        self, value: str, requested_value: str, protected_entities: Optional[str] = None
    ) -> str:
        """
        Updates a value from within the context of the spec file with a new value,
        but tries to preserve substitutions of locally defined macros and tags,
        updating the respective macro definitions and tag values instead.

        Args:
            value: Value to update.
            requested_value: Requested new value.
            protected_entities: Regular expression specifying protected tags and macro definitions,
              ensuring their values won't be updated.

        Returns:
            Updated value. Can be equal to the original value.
        """

        @dataclass
        class Entity:
            value: str
            type: Type
            locked: bool = False
            updated: bool = False

        protected_regex = re.compile(
            # (?!) doesn't match anything
            protected_entities or "(?!)",
            re.IGNORECASE,
        )
        # collect modifiable entities
        entities = {}
        with self.macro_definitions() as macro_definitions:
            entities.update(
                {
                    md.name: Entity(md.body, type(md))
                    for md in macro_definitions
                    if not protected_regex.match(md.name)
                    and not md.name.endswith(")")  # skip macro definitions with options
                }
            )
        # order matters here - if there is a macro definition redefining a tag,
        # we want to update the tag, not the macro definition
        with self.tags() as tags:
            entities.update(
                {
                    t.name.lower(): Entity(t.value, type(t))
                    for t in tags
                    if not protected_regex.match(t.name)
                }
            )
        # tags can be referenced as %{tag} or %{TAG}
        entities.update({k.upper(): v for k, v in entities.items() if v.type == Tag})

        def update(value, requested_value):
            regex, template = ValueParser.construct_regex(
                value, entities.keys(), context=self
            )
            m = regex.match(requested_value)
            if m:
                d = m.groupdict()
                for grp, val in d.items():
                    if grp.startswith(SUBSTITUTION_GROUP_PREFIX):
                        continue
                    if entities[grp].locked:
                        # avoid infinite recursion
                        return requested_value
                    entities[grp].locked = True
                    try:
                        entities[grp].value = update(entities[grp].value, val)
                    finally:
                        entities[grp].locked = False
                        entities[grp].updated = True
                return template.substitute(d)
            # no match, simply return the requested value
            return requested_value

        result = update(value, requested_value)
        # synchronize back any changes
        with self.macro_definitions() as macro_definitions:
            for n, v in [
                (n, v)
                for n, v in entities.items()
                if v.updated and v.type == MacroDefinition
            ]:
                getattr(macro_definitions, n).body = v.value
        with self.tags() as tags:
            for n, v in [
                (n, v) for n, v in entities.items() if v.updated and v.type == Tag
            ]:
                getattr(tags, n).value = v.value
        return result

    def update_tag(
        self, name: str, value: str, protected_entities: str = ".*name"
    ) -> None:
        """
        Updates value of the given tag, trying to preserve substitutions
        of locally defined macros and tags, updating the respective macro definitions
        and tag values instead.

        Args:
            name: Tag name.
            value: Requested new value.
            protected_entities: Regular expression specifying protected tags and macro definitions,
              ensuring their values won't be updated.
        """
        with self.tags() as tags:
            original_value = getattr(tags, name).value
        # we can't use update_value() within the context manager, because any changes
        # made by it to tags or macro definitions would be thrown away
        updated_value = self.update_value(
            original_value, value, protected_entities=protected_entities
        )
        with self.tags() as tags:
            getattr(tags, name).value = updated_value
