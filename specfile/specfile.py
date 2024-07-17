# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime
import logging
import re
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Optional, Tuple, Type, Union, cast

import rpm

from specfile.changelog import Changelog, ChangelogEntry, guess_packager
from specfile.context_management import ContextManager
from specfile.exceptions import (
    SourceNumberException,
    SpecfileException,
    UnterminatedMacroException,
)
from specfile.formatter import formatted
from specfile.macro_definitions import (
    CommentOutStyle,
    MacroDefinition,
    MacroDefinitions,
)
from specfile.macros import Macro, Macros
from specfile.prep import Prep
from specfile.sections import Section, Sections
from specfile.sourcelist import Sourcelist
from specfile.sources import Patches, Sources
from specfile.spec_parser import SpecParser
from specfile.tags import Tag, Tags
from specfile.value_parser import (
    SUBSTITUTION_GROUP_PREFIX,
    ConditionalMacroExpansion,
    EnclosedMacroSubstitution,
    MacroSubstitution,
    ValueParser,
)

logger = logging.getLogger(__name__)


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
        macros: Optional[List[Tuple[str, Optional[str]]]] = None,
        force_parse: bool = False,
    ) -> None:
        """
        Initializes a specfile object.

        Args:
            path: Path to the spec file.
            sourcedir: Path to sources and patches.
            autosave: Whether to automatically save any changes made.
            macros: List of extra macro definitions.
            force_parse: Whether to attempt to parse the spec file even if one or more
                sources required to be present at parsing time are not available.
                Such sources include sources referenced from shell expansions
                in tag values and sources included using the _%include_ directive.
        """
        self.autosave = autosave
        self._path = Path(path)
        self._lines, self._trailing_newline = self._read_lines(self._path)
        self._parser = SpecParser(
            Path(sourcedir or self.path.parent), macros, force_parse
        )
        self._parser.parse(str(self))
        self._dump_debug_info("After initial parsing")

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
        return "\n".join(self._lines) + ("\n" if self._trailing_newline else "")

    def __enter__(self) -> "Specfile":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[types.TracebackType],
    ) -> None:
        self.save()

    def _dump_debug_info(self, message) -> None:
        logger.debug(
            f"DBG: {message}:\n"
            f"  {self!r} @ 0x{id(self):012x}\n"
            f"  {self._parser!r} @ 0x{id(self._parser):012x}\n"
            f"  {self._parser.spec!r} @ 0x{id(self._parser.spec):012x}"
        )

    @staticmethod
    def _read_lines(path: Path) -> Tuple[List[str], bool]:
        content = path.read_text(encoding="utf8", errors="surrogateescape")
        return content.splitlines(), content[-1] == "\n"

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
    def macros(self) -> List[Tuple[str, Optional[str]]]:
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
        self._dump_debug_info("`rpm_spec` property, before parsing")
        self._parser.parse(str(self))
        self._dump_debug_info("`rpm_spec` property, after parsing")
        return self._parser.spec

    def reload(self) -> None:
        """Reloads the spec file content."""
        self._lines, self._trailing_newline = self._read_lines(self.path)

    def save(self) -> None:
        """Saves the spec file content."""
        self.path.write_text(str(self), encoding="utf8", errors="surrogateescape")

    def expand(
        self,
        expression: str,
        extra_macros: Optional[List[Tuple[str, Optional[str]]]] = None,
        skip_parsing: bool = False,
    ) -> str:
        """
        Expands an expression in the context of the spec file.

        Args:
            expression: Expression to expand.
            extra_macros: Extra macros to be defined before expansion is performed.
            skip_parsing: Do not parse the spec file before expansion is performed.
                Defaults to `False`. Mutually exclusive with `extra_macros`. Set this to `True`
                only if you are certain that the global macro context is up-to-date.

        Returns:
            Expanded expression.
        """
        if not skip_parsing or extra_macros is not None:
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
            macro_definitions = MacroDefinitions.parse(
                lines, with_conditions=True, context=self
            )
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
            if isinstance(section, str):
                section = cast(Section, getattr(sections, section))
            tags = Tags.parse(section, context=self)
            try:
                yield tags
            finally:
                section.data = tags.get_raw_section_data()

    @ContextManager
    def changelog(
        self, section: Optional[Section] = None
    ) -> Generator[Optional[Changelog], None, None]:
        """
        Context manager for accessing changelog.

        Args:
            section: Optional `Section` instance to be processed. If not set, the first
                _%changelog_ section (if any) will be processed.

        Yields:
            Spec file changelog as `Changelog` object or `None` if there is no _%changelog_ section.
        """
        with self.sections() as sections:
            if section is None:
                try:
                    section = sections.changelog
                except AttributeError:
                    section = None
            if section is None:
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
        Context manager for accessing _%prep_ section.

        Yields:
            Spec file _%prep_ section as `Prep` object.
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
                    (
                        cast(List[Sourcelist], list(zip(*sourcelists))[1])
                        if sourcelists
                        else []
                    ),
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
                    (
                        cast(List[Sourcelist], list(zip(*patchlists))[1])
                        if patchlists
                        else []
                    ),
                    allow_duplicates,
                    default_to_implicit_numbering,
                    default_source_number_digits,
                    context=self,
                )
            finally:
                for section, patchlist in patchlists:
                    section.data = patchlist.get_raw_section_data()

    @property
    def has_autorelease(self) -> bool:
        """Whether the spec file uses _%autorelease_."""
        for node in ValueParser.flatten(ValueParser.parse(self.raw_release)):
            if (
                isinstance(node, (MacroSubstitution, EnclosedMacroSubstitution))
                and node.name == "autorelease"
            ):
                return True
        return False

    @staticmethod
    def contains_autochangelog(section: Section) -> bool:
        """
        Determines if the specified section contains the _%autochangelog_ macro.

        Args:
            section: Section to examine.

        Returns:
            `True` if the section contains _%autochangelog_, `False` otherwise.
        """
        for line in section:
            if line.lstrip().startswith("#"):
                # skip comments
                continue
            try:
                for node in ValueParser.flatten(ValueParser.parse(line)):
                    if (
                        isinstance(node, (MacroSubstitution, EnclosedMacroSubstitution))
                        and node.name == "autochangelog"
                    ):
                        return True
            except UnterminatedMacroException:
                # ignore unparseable lines
                continue
        return False

    @property
    def has_autochangelog(self) -> bool:
        """Whether the spec file uses _%autochangelog_."""
        with self.sections() as sections:
            # there could be multiple changelog sections, consider all of them
            for section in sections:
                if not section.normalized_id == "changelog":
                    continue
                if self.contains_autochangelog(section):
                    return True
            return False

    def add_changelog_entry(
        self,
        entry: Union[str, List[str]],
        author: Optional[str] = None,
        email: Optional[str] = None,
        timestamp: Optional[Union[datetime.date, datetime.datetime]] = None,
        evr: Optional[str] = None,
    ) -> None:
        """
        Adds a new _%changelog_ entry. Does nothing if there is no _%changelog_ section
        or if _%autochangelog_ is being used.

        If not specified, author and e-mail will be automatically determined, if possible.
        Timestamp, if not set, will be set to current time (in local timezone).

        Args:
            entry: Entry text or list of entry lines.
            author: Author of the entry.
            email: E-mail of the author.
            timestamp: Timestamp of the entry.
                Supply `datetime` rather than `date` for extended format.
            evr: Override the EVR part of the changelog entry.
                Macros will be expanded automatically. By default, the function
                determines the appropriate value based on the spec file current
                _%{epoch}_, _%{version}_, and _%{release}_ values.
        """
        with self.sections() as sections:
            # there could be multiple changelog sections, update all of them
            for section in sections:
                if not section.normalized_id == "changelog":
                    continue
                if self.contains_autochangelog(section):
                    continue
                if evr is None:
                    evr = "%{?epoch:%{epoch}:}%{version}-%{release}"
                with self.changelog(section) as changelog:
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
                            timestamp = datetime.datetime.now(
                                datetime.timezone.utc
                            ).date()
                    if author is None:
                        author = guess_packager()
                        if not author:
                            raise SpecfileException("Failed to auto-detect author")
                    elif email is not None:
                        author += f" <{email}>"
                    if changelog:
                        # try to preserve padding of day of month
                        padding = max(
                            (e.day_of_month_padding for e in reversed(changelog)),
                            key=len,
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
            release: Release string, defaults to "1".
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
            SourceNumberException: If the specified patch number is not higher
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

        def expand(s):
            result = self.expand(s, skip_parsing=getattr(expand, "skip_parsing", False))
            # parse only once
            expand.skip_parsing = True
            return result

        @dataclass
        class Entity:
            name: str
            value: str
            type: Type
            position: int
            disabled: bool = False
            locked: bool = False
            updated: bool = False
            flip_pending: bool = False

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
                        md.name,
                        md.body,
                        type(md),
                        md.get_position(macro_definitions),
                        md.commented_out or not expand(md.body),
                    )
                    for md in macro_definitions
                    if md.valid
                    and not protected_regex.match(md.name)
                    and not md.name.endswith(")")  # skip macro definitions with options
                ]
            )
        with self.tags() as tags:
            entities.extend(
                [
                    Entity(t.name.lower(), t.value, type(t), t.get_position(tags))
                    for t in tags
                    if t.valid and not protected_regex.match(t.name)
                ]
            )
        entities.sort(key=lambda e: e.position)

        def find_reference(entity, value):
            def traverse(nodes):
                for node in nodes:
                    if isinstance(
                        node,
                        (
                            MacroSubstitution,
                            EnclosedMacroSubstitution,
                            ConditionalMacroExpansion,
                        ),
                    ):
                        if (
                            entity.type == Tag
                            and entity.name == node.name.lower()
                            or entity.name == node.name
                        ):
                            return True
                    if isinstance(node, ConditionalMacroExpansion):
                        if traverse(node.body):
                            return True
                return False

            return traverse(ValueParser.parse(value))

        def update(value, requested_value, position):
            if value == requested_value:
                # nothing to do
                return requested_value

            modifiable_entities = {
                e.name
                for e in entities
                if e.position < position and (not e.flip_pending or e.disabled)
            }
            # tags can be referenced as %{tag} or %{TAG}
            modifiable_entities.update(
                e.name.upper()
                for e in entities
                if e.position < position and e.type == Tag
            )
            flippable_entities = {
                e.name
                for e in entities
                if e.position < position
                and e.type == MacroDefinition
                and not e.flip_pending
            }

            # in case the value doesn't match after trying with flippable entities
            # do a second pass without them
            for flippable_ents in (flippable_entities, set()):
                regex, template, entities_to_flip = ValueParser.construct_regex(
                    value, modifiable_entities, flippable_ents, context=self
                )
                m = regex.match(requested_value)
                if not m:
                    continue
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
                    if find_reference(entity, val):
                        # avoid updating entity value if the entity is referenced from the new value
                        return requested_value
                    entity.locked = True
                    try:
                        entity.value = update(entity.value, val, entity.position)
                    finally:
                        entity.locked = False
                        entity.updated = True
                for entity in entities:
                    if entity.position < position and entity.name in entities_to_flip:
                        entity.flip_pending = True
                return template.substitute(d)
            # no match, simply return the requested value
            return requested_value

        result = update(value, requested_value, position)
        # synchronize back any changes
        with self.macro_definitions() as macro_definitions:
            for entity in entities:
                if entity.type != MacroDefinition:
                    continue
                macro_definition = macro_definitions.get(entity.name, entity.position)
                if entity.updated:
                    macro_definition.body = entity.value
                    macro_definition.commented_out = False
                elif entity.flip_pending:
                    macro_definition.commented_out = not entity.disabled
        with self.tags() as tags:
            for entity in entities:
                if entity.type != Tag:
                    continue
                tag = tags.get(entity.name, entity.position)
                if entity.updated:
                    tag.value = entity.value
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

    def update_version(
        self,
        version: str,
        prerelease_suffix_pattern: Optional[str] = None,
        prerelease_suffix_macro: Optional[str] = None,
        comment_out_style: CommentOutStyle = CommentOutStyle.DNL,
    ) -> None:
        """
        Updates spec file version.

        If `prerelease_suffix_pattern` is not set, this method is equivalent
        to calling `update_tag("Version", version)`.
        If `prerelease_suffix_pattern` is set and the specified version matches it,
        the detected pre-release suffix is prepended with '~' (any existing delimiter
        is removed) before updating Version to ensure proper sorting by RPM.
        If `prerelease_suffix_macro` is also set and such macro definition exists,
        it is commented out or uncommented accordingly before updating Version.

        Args:
            version: Version string.
            prerelease_suffix_pattern: Regular expression specifying recognized
                pre-release suffixes. The first capturing group must capture the delimiter
                between base version and pre-release suffix and can be empty in case
                there is no delimiter.
            prerelease_suffix_macro: Macro definition that controls whether spec file
                version is a pre-release and contains the pre-release suffix.
                To be commented out or uncommented accordingly.
            comment_out_style: Style of commenting out `prerelease_suffix_macro`.
                See `CommentOutStyle`. Defaults to `CommentOutStyle.DNL`.

        Raises:
            SpecfileException: If `prerelease_suffix_pattern` is invalid.
        """

        def update_macro(prerelease_detected):
            if not prerelease_suffix_macro:
                return
            with self.macro_definitions() as macro_definitions:
                try:
                    macro = macro_definitions.get(prerelease_suffix_macro)
                except (IndexError, ValueError):
                    return
                if not macro.commented_out:
                    macro.comment_out_style = comment_out_style
                macro.commented_out = not prerelease_detected

        def handle_prerelease(version):
            if not prerelease_suffix_pattern:
                return version
            m = re.match(f"^.*?{prerelease_suffix_pattern}$", version, re.IGNORECASE)
            if not m:
                update_macro(False)
                return version
            try:
                base_end, suffix_start = m.span(1)
            except IndexError:
                raise SpecfileException("Invalid pre-release pattern")
            update_macro(True)
            return version[:base_end] + "~" + version[suffix_start:]

        self.update_tag("Version", handle_prerelease(version))

    @staticmethod
    def _bump_release_string(release_string: str) -> str:
        """
        Bumps release string. Follows the logic of `rpmdev-bumpspec`.

        Args:
            release_string: Release string to be bumped.

        Returns:
            Bumped release string.
        """
        m = re.match(
            r"^(?P<func>%release_func\s+)?(?P<pre>0\.)?(?P<rel>\d+)(?P<post>.*)$",
            release_string,
        )
        if m and (
            m.group("pre")
            or all(x not in m.group("post") for x in ["alpha", "beta", "rc"])
        ):
            return (
                (m.group("func") or "")
                + (m.group("pre") or "")
                + str(int(m.group("rel")) + 1)
                + m.group("post")
            )
        m = re.match(r"^(?P<pre>.+\.)(?P<rel>\d+)$", release_string)
        if m:
            return m.group("pre") + str(int(m.group("rel")) + 1)
        return release_string + ".1"

    def bump_release(self) -> None:
        """
        Tries to bump release. Follows the logic of `rpmdev-bumpspec`, first trying to update
        macro definitions that seem to define a release, then trying to update value
        of the Release tag.
        """
        if self.has_autorelease:
            return

        with self.macro_definitions() as macro_definitions:
            for md in macro_definitions:
                if md.name.lower() in ["release", "baserelease"]:
                    md.body = self._bump_release_string(md.body)
                    return

        self.raw_release = self._bump_release_string(self.raw_release)
