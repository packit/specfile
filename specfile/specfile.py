# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime
import re
import subprocess
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Optional, Tuple, Type, Union

import rpm

from specfile.changelog import Changelog, ChangelogEntry
from specfile.context_management import ContextManager
from specfile.exceptions import SourceNumberException, SpecfileException
from specfile.formatter import formatted
from specfile.macro_definitions import MacroDefinition, MacroDefinitions
from specfile.macros import Macro, Macros
from specfile.prep import Prep
from specfile.sections import Section, Sections
from specfile.sourcelist import Sourcelist
from specfile.sources import Patches, Sources
from specfile.spec_parser import SpecParser
from specfile.tags import Tag, Tags
from specfile.value_parser import SUBSTITUTION_GROUP_PREFIX, ValueParser


class Specfile:
    """
    Class that represents a spec file.

    Attributes:
        autosave: Whether to automatically save any changes made.
    """

    def __init__(
        self,
        path: Union[Path, str],
        sourcedir: Optional[Union[Path, str]] = None,
        autosave: bool = False,
        macros: Optional[List[Tuple[str, str]]] = None,
        force_parse: bool = False,
    ) -> None:
        """
        Constructs a `Specfile` object.

        Args:
            path: Path to the spec file.
            sourcedir: Path to sources and patches.
            autosave: Whether to automatically save any changes made.
            macros: List of extra macro definitions.
            force_parse: Whether to attempt to parse the spec file even if one or more
              sources required to be present at parsing time are not available.
              Such sources include sources referenced from shell expansions
              in tag values and sources included using the %include directive.

        Returns:
            Constructed instance of `Specfile` class.
        """
        self.autosave = autosave
        self._path = Path(path)
        self._lines = self.path.read_text().splitlines()
        self._parser = SpecParser(
            Path(sourcedir or self.path.parent), macros, force_parse
        )
        # parse here to fail early on parsing errors
        self._parser.parse(str(self))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Specfile):
            return NotImplemented
        return (
            self.autosave == other.autosave
            and self._path == other._path
            and self._lines == other._lines
            and self._parser == other._parser
        )

    @formatted
    def __repr__(self) -> str:
        return (
            f"Specfile({self.path!r}, {self._parser.sourcedir!r}, {self.autosave!r}, "
            f"{self._parser.macros!r}, {self._parser.force_parse!r})"
        )

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

    @property
    def path(self) -> Path:
        """Path to the spec file."""
        return self._path

    @path.setter
    def path(self, value: Union[Path, str]) -> None:
        self._path = Path(value)

    @property
    def sourcedir(self) -> Path:
        """Path to sources and patches."""
        return self._parser.sourcedir

    @sourcedir.setter
    def sourcedir(self, value: Union[Path, str]) -> None:
        self._parser.sourcedir = Path(value)

    @property
    def macros(self) -> List[Tuple[str, str]]:
        """List of extra macro definitions."""
        return self._parser.macros

    @property
    def force_parse(self) -> bool:
        """
        Whether to attempt to parse the spec file even if one or more
        sources required to be present at parsing time are not available.
        """
        return self._parser.force_parse

    @force_parse.setter
    def force_parse(self, value: bool) -> None:
        self._parser.force_parse = value

    @property
    def tainted(self) -> bool:
        """
        Indication that parsing of the spec file was forced and one or more
        sources required to be present at parsing time were not available
        and were replaced with dummy files.
        """
        self._parser.parse(str(self))
        return self._parser.tainted

    @property
    def rpm_spec(self) -> rpm.spec:
        """Underlying `rpm.spec` instance."""
        self._parser.parse(str(self))
        return self._parser.spec

    def reload(self) -> None:
        """Reload the spec file content."""
        self._lines = self.path.read_text().splitlines()

    def save(self) -> None:
        """Save the spec file content."""
        self.path.write_text(str(self))

    def expand(
        self,
        expression: str,
        extra_macros: Optional[List[Tuple[str, str]]] = None,
        skip_parsing: bool = False,
    ) -> str:
        """
        Expands an expression in the context of the spec file.

        Args:
            expression: Expression to expand.
            extra_macros: Extra macros to be defined before expansion is performed.
            skip_parsing: Do not parse the spec file before expansion is performed.
              Defaults to False. Mutually exclusive with extra_macros. Set this to True
              only if you are certain that the global macro context is up-to-date.

        Returns:
            Expanded expression.
        """
        if not skip_parsing:
            self._parser.parse(str(self), extra_macros)
        return Macros.expand(expression)

    def get_active_macros(self) -> List[Macro]:
        """
        Gets active macros in the context of the spec file.

        This includes built-in RPM macros, macros loaded from macro files
        and macros defined in the spec file itself.

        Returns:
            List of `Macro` objects.
        """
        self._parser.parse(str(self))
        return Macros.dump()

    @ContextManager
    def lines(self) -> Generator[List[str], None, None]:
        """
        Context manager for accessing spec file lines.

        Yields:
            Spec file lines as list of strings.
        """
        try:
            yield self._lines
        finally:
            if self.autosave:
                self.save()

    @ContextManager
    def macro_definitions(self) -> Generator[MacroDefinitions, None, None]:
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

    @ContextManager
    def sections(self) -> Generator[Sections, None, None]:
        """
        Context manager for accessing spec file sections.

        Yields:
            Spec file sections as `Sections` object.
        """
        with self.lines() as lines:
            sections = Sections.parse(lines, context=self)
            try:
                yield sections
            finally:
                lines[:] = sections.get_raw_data()

    @property
    def parsed_sections(self) -> Sections:
        """Parsed spec file sections."""
        return Sections.parse(self.rpm_spec.parsed.splitlines())

    @ContextManager
    def tags(
        self, section: Union[str, Section] = "package"
    ) -> Generator[Tags, None, None]:
        """
        Context manager for accessing tags in a specified section.

        Args:
            section: Name of the requested section or an existing `Section` instance.
              Defaults to preamble.

        Yields:
            Tags in the section as `Tags` object.
        """
        with self.sections() as sections:
            if isinstance(section, Section):
                raw_section = section
                parsed_section = getattr(self.parsed_sections, section.id, None)
            else:
                raw_section = getattr(sections, section)
                parsed_section = getattr(self.parsed_sections, section, None)
            tags = Tags.parse(raw_section, parsed_section)
            try:
                yield tags
            finally:
                raw_section.data = tags.get_raw_section_data()

    @ContextManager
    def changelog(self) -> Generator[Optional[Changelog], None, None]:
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

    @ContextManager
    def prep(self) -> Generator[Optional[Prep], None, None]:
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

    @ContextManager
    def sources(
        self,
        allow_duplicates: bool = False,
        default_to_implicit_numbering: bool = False,
        default_source_number_digits: int = 1,
    ) -> Generator[Sources, None, None]:
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
                (s, Sourcelist.parse(s, context=self))
                for s in sections
                if s.id == "sourcelist"
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

    @ContextManager
    def patches(
        self,
        allow_duplicates: bool = False,
        default_to_implicit_numbering: bool = False,
        default_source_number_digits: int = 1,
    ) -> Generator[Patches, None, None]:
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
                (s, Sourcelist.parse(s, context=self))
                for s in sections
                if s.id == "patchlist"
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
        evr: Optional[str] = None,
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
            evr: Override the EVR part of the changelog entry.
              Macros will be expanded automatically. By default, the function
              determines the appropriate value based on the specfile's current
              %{epoch}, %{version}, and %{release} values.
        """
        if self.has_autochangelog:
            return
        if evr is None:
            evr = "%{?epoch:%{epoch}:}%{version}-%{release}"
        with self.changelog() as changelog:
            if changelog is None:
                return
            evr = self.expand(evr, extra_macros=[("dist", "")])
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

    epoch = _tag("epoch", "Epoch as stored in the spec file.")
    expanded_epoch = _expanded_tag("epoch", "Epoch with macros expanded.")

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
        return self.expand(self.release, extra_macros=[("dist", "")])

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
        self,
        value: str,
        requested_value: str,
        position: int,
        protected_entities: Optional[str] = None,
    ) -> str:
        """
        Updates a value from within the context of the spec file with a new value,
        but tries to preserve substitutions of locally defined macros and tags,
        updating the respective macro definitions and tag values instead.

        Args:
            value: Value to update.
            requested_value: Requested new value.
            position: Position (line number) of the value in the spec file.
            protected_entities: Regular expression specifying protected tags and macro definitions,
              ensuring their values won't be updated.

        Returns:
            Updated value. Can be equal to the original value.
        """

        @dataclass
        class Entity:
            name: str
            value: str
            type: Type
            position: int
            locked: bool = False
            updated: bool = False

        protected_regex = re.compile(
            # (?!) doesn't match anything
            protected_entities or "(?!)",
            re.IGNORECASE,
        )
        # collect modifiable entities
        entities = []
        with self.macro_definitions() as macro_definitions:
            entities.extend(
                [
                    Entity(
                        md.name, md.body, type(md), md.get_position(macro_definitions)
                    )
                    for md in macro_definitions
                    if not protected_regex.match(md.name)
                    and not md.name.endswith(")")  # skip macro definitions with options
                ]
            )
        with self.tags() as tags:
            entities.extend(
                [
                    Entity(t.name.lower(), t.value, type(t), t.get_position(tags))
                    for t in tags
                    if not protected_regex.match(t.name)
                ]
            )
        entities.sort(key=lambda e: e.position)

        def update(value, requested_value, position):
            modifiable_entities = {e.name for e in entities if e.position < position}
            # tags can be referenced as %{tag} or %{TAG}
            modifiable_entities.update(
                e.name.upper()
                for e in entities
                if e.position < position and e.type == Tag
            )
            regex, template = ValueParser.construct_regex(
                value, modifiable_entities, context=self
            )
            m = regex.match(requested_value)
            if m:
                d = m.groupdict()
                for grp, val in d.items():
                    if grp.startswith(SUBSTITUTION_GROUP_PREFIX):
                        continue
                    # find the closest matching entity
                    entity = [
                        e
                        for e in entities
                        if e.position < position
                        and (
                            e.name == grp
                            and e.type == MacroDefinition
                            or e.name == grp.lower()
                            and e.type == Tag
                        )
                    ][-1]
                    if entity.locked:
                        # avoid infinite recursion
                        return requested_value
                    entity.locked = True
                    try:
                        entity.value = update(entity.value, val, entity.position)
                    finally:
                        entity.locked = False
                        entity.updated = True
                return template.substitute(d)
            # no match, simply return the requested value
            return requested_value

        result = update(value, requested_value, position)
        # synchronize back any changes
        with self.macro_definitions() as macro_definitions:
            for entity in [
                e for e in entities if e.updated and e.type == MacroDefinition
            ]:
                getattr(macro_definitions, entity.name).body = entity.value
        with self.tags() as tags:
            for entity in [e for e in entities if e.updated and e.type == Tag]:
                getattr(tags, entity.name).value = entity.value
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
            tag = getattr(tags, name)
            original_value = tag.value
            position = tag.get_position(tags)
        # we can't use update_value() within the context manager, because any changes
        # made by it to tags or macro definitions would be thrown away
        updated_value = self.update_value(
            original_value, value, position, protected_entities=protected_entities
        )
        with self.tags() as tags:
            getattr(tags, name).value = updated_value
