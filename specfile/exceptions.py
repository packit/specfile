# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from typing import List


class SpecfileException(Exception):
    """Base class for all library exceptions."""


class RPMException(SpecfileException):
    """RPM exception."""

    def __init__(self, stderr: List[bytes]) -> None:
        super().__init__()
        self.stderr = stderr

    def __str__(self) -> str:
        for rline in self.stderr:
            line = rline.decode().rstrip()
            if line.startswith("error:"):
                return line.split("error: ")[1]
        return "\n" + b"".join(self.stderr).decode()


class MacroRemovalException(SpecfileException):
    """Impossible to remove a RPM macro."""


class OptionsException(SpecfileException):
    """Unparseable option string."""


class UnterminatedMacroException(SpecfileException):
    """Macro starts but doesn't end."""


class DuplicateSourceException(SpecfileException):
    """Source with the same location already exists."""


class SourceNumberException(SpecfileException):
    """Incorrect numbering of sources."""
