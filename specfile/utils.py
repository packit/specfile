# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import contextlib
import io
import os
import re
import sys
import tempfile
from typing import Iterator, List

from specfile.constants import ARCH_NAMES
from specfile.exceptions import SpecfileException


class EVR(collections.abc.Hashable):
    """Class representing Epoch-Version-Release combination."""

    _regex = r"(?:(\d+):)?([^-]+?)(?:-([^-]+))?"

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
        m = re.match(f"^{cls._regex}$", evr)
        if not m:
            raise SpecfileException("Invalid EVR string.")
        e, v, r = m.groups()
        return cls(epoch=int(e) if e else 0, version=v, release=r or "")


class NEVR(EVR):
    """Class representing Name-Epoch-Version-Release combination."""

    _regex = r"(.+?)-" + EVR._regex

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
        m = re.match(f"^{cls._regex}$", nevr)
        if not m:
            raise SpecfileException("Invalid NEVR string.")
        n, e, v, r = m.groups()
        return cls(name=n, epoch=int(e) if e else 0, version=v, release=r or "")


class NEVRA(NEVR):
    """Class representing Name-Epoch-Version-Release-Arch combination."""

    _arches_regex = "(" + "|".join(re.escape(a) for a in ARCH_NAMES | {"noarch"}) + ")"
    _regex = NEVR._regex + r"\." + _arches_regex

    def __init__(
        self, *, name: str, version: str, release: str, arch: str, epoch: int = 0
    ) -> None:
        if not re.match(f"^{self._arches_regex}$", arch):
            raise SpecfileException("Invalid architecture name.")
        self.arch = arch
        super().__init__(name=name, epoch=epoch, version=version, release=release)

    def _key(self) -> tuple:
        return self.name, self.epoch, self.version, self.release, self.arch

    def __repr__(self) -> str:
        return (
            f"NEVRA(name='{self.name}', epoch={self.epoch}, "
            f"version='{self.version}', release='{self.release}', "
            f"arch='{self.arch}')"
        )

    def __str__(self) -> str:
        return super().__str__() + f".{self.arch}"

    @classmethod
    def from_string(cls, nevra: str) -> "NEVRA":
        m = re.match(f"^{cls._regex}$", nevra)
        if not m:
            raise SpecfileException("Invalid NEVRA string.")
        n, e, v, r, a = m.groups()
        return cls(name=n, epoch=int(e) if e else 0, version=v, release=r, arch=a)


@contextlib.contextmanager
def capture_stderr() -> Iterator[List[bytes]]:
    """
    Context manager for capturing output to stderr. A stderr output of anything run
    in its context will be captured in the target variable of the with statement.

    Yields:
        List of captured lines.
    """
    fileno = sys.__stderr__.fileno()
    with tempfile.TemporaryFile() as stderr, os.fdopen(os.dup(fileno)) as backup:
        sys.stderr.flush()
        os.dup2(stderr.fileno(), fileno)
        data: List[bytes] = []
        try:
            yield data
        finally:
            sys.stderr.flush()
            os.dup2(backup.fileno(), fileno)
            stderr.flush()
            stderr.seek(0, io.SEEK_SET)
            data.extend(stderr.readlines())


def get_filename_from_location(location: str) -> str:
    """
    Extracts filename from given source location.

    Follows RPM logic - target filename can be specified in URL fragment.

    Args:
        location: Location to extract filename from.

    Returns:
        Extracted filename that can be empty if there is none.
    """
    slash = location.rfind("/")
    if slash < 0:
        return location
    return location[slash + 1 :].split("=")[-1]
