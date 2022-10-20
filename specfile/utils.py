# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import re
import urllib.parse
from pathlib import Path

from specfile.exceptions import SpecfileException


class EVR(collections.abc.Hashable):
    """Class representing Epoch-Version-Release combination."""

    def __init__(self, *, version: str, release: str = "", epoch: int = 0) -> None:
        self.epoch = epoch
        self.version = version
        self.release = release

    def _key(self) -> tuple:
        return self.epoch, self.version, self.release

    def __hash__(self) -> int:
        return hash(self._key())

    def __eq__(self, other: object) -> bool:
        if type(other) != self.__class__:
            return NotImplemented
        return self._key() == other._key()

    def __repr__(self) -> str:
        return f"EVR(epoch={self.epoch}, version='{self.version}', release='{self.release}')"

    def __str__(self) -> str:
        epoch = f"{self.epoch}:" if self.epoch > 0 else ""
        release = f"-{self.release}" if self.release else ""
        return f"{epoch}{self.version}{release}"

    @classmethod
    def from_string(cls, evr: str) -> "EVR":
        m = re.match(r"^(?:(\d+):)?([^-]+?)(?:-([^-]+))?$", evr)
        if not m:
            raise SpecfileException("Invalid EVR string.")
        e, v, r = m.groups()
        return cls(epoch=int(e) if e else 0, version=v, release=r or "")


class NEVR(EVR):
    """Class representing Name-Epoch-Version-Release combination."""

    def __init__(
        self, *, name: str, version: str, release: str = "", epoch: int = 0
    ) -> None:
        self.name = name
        super().__init__(epoch=epoch, version=version, release=release)

    def _key(self) -> tuple:
        return self.name, self.epoch, self.version, self.release

    def __repr__(self) -> str:
        return (
            f"NEVR(name='{self.name}', epoch={self.epoch}, "
            f"version='{self.version}', release='{self.release}')"
        )

    def __str__(self) -> str:
        return f"{self.name}-" + super().__str__()

    @classmethod
    def from_string(cls, nevr: str) -> "NEVR":
        m = re.match(r"^(.+?)-(?:(\d+):)?([^-]+?)(?:-([^-]+))?$", nevr)
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
