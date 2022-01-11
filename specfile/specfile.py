# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import contextlib
import types
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Type, Union

from specfile.rpm import RPM, Macros
from specfile.sections import Sections
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

    def expand(self, expression: str) -> str:
        """
        Expands an expression in the context of the spec file.

        Args:
            expression: Expression to expand.

        Returns:
            Expanded expression.
        """
        RPM.parse(str(self._sections), self.sourcedir, self.macros)
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
                raw_section.data = tags.reassemble()
