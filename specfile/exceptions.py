# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from typing import List


class SpecfileException(Exception):
    """Something went wrong during our execution."""

    pass


class RPMException(SpecfileException):
    """Exception related to RPM."""

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
    """Exception related to failed removal of RPM macros."""


class MacroOptionsException(SpecfileException):
    """Exception related to processing macro options."""
