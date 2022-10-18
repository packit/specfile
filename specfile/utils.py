# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from specfile.exceptions import SpecfileException


@dataclass(kw_only=True)
class EVR:
    """Class representing Epoch-Version-Release combination."""

    epoch: int = 0
    version: str
    release: str = ""

    def __str__(self) -> str:
        epoch = f"{self.epoch}:" if self.epoch > 0 else ""
        release = f"-{self.release}" if self.release else ""
        return f"{epoch}{self.version}{release}"

    @classmethod
    def from_string(cls, evr: str) -> "EVR":
        m = re.match(r"^(?:(\d+):)?(.*?)(?:-([^-]*))?$", evr)
        if not m:
            raise SpecfileException("Invalid EVR string.")
        e, v, r = m.groups()
        return cls(epoch=int(e) if e else 0, version=v, release=r or "")


@dataclass(kw_only=True)
class NEVR:
    """Class representing Name-Epoch-Version-Release combination."""

    name: str
    epoch: int = 0
    version: str
    release: str = ""

    def __str__(self) -> str:
        epoch = f"{self.epoch}:" if self.epoch > 0 else ""
        release = f"-{self.release}" if self.release else ""
        return f"{self.name}-{epoch}{self.version}{release}"

    @classmethod
    def from_string(cls, nevr: str) -> "NEVR":
        m = re.match(r"^(.*?)-(?:(\d+):)?([^-]*?)(?:-([^-]*))?$", nevr)
        if not m:
            raise SpecfileException("Invalid NEVR string.")
        n, e, v, r = m.groups()
        return cls(name=n, epoch=int(e) if e else 0, version=v, release=r or "")


def get_filename_from_location(location: str) -> str:
    """
    Extracts filename from given source location.

    Follows RPM logic - target filename can be specified in URL fragment.

    Args:
        location: Location to extract filename from.

    Returns:
        Extracted filename that can be empty if there is none.
    """
    url = urllib.parse.urlsplit(location)
    if url.fragment:
        if "/" in url.fragment:
            return Path(url.fragment).name.split("=")[-1]
        return Path(f"{url.path}#{url.fragment}").name
    return Path(url.path).name
