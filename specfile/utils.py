# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import re
import sys
from typing import TYPE_CHECKING, Tuple

import rpm

from specfile.constants import ARCH_NAMES
from specfile.exceptions import SpecfileException, UnterminatedMacroException
from specfile.formatter import formatted
from specfile.value_parser import ConditionalMacroExpansion, ValueParser


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

    def _rpm_evr_tuple(self) -> Tuple[str, str, str]:
        return str(self.epoch), self.version or "0", self.release

    def _cmp(self, other: "EVR") -> int:
        return rpm.labelCompare(self._rpm_evr_tuple(), other._rpm_evr_tuple())

    def __lt__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return self._cmp(other) < 0

    def __le__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return self._cmp(other) <= 0

    def __eq__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return self._cmp(other) == 0

    def __ne__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return self._cmp(other) != 0

    def __ge__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return self._cmp(other) >= 0

    def __gt__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return self._cmp(other) > 0

    @formatted
    def __repr__(self) -> str:
        return f"EVR(epoch={self.epoch!r}, version={self.version!r}, release={self.release!r})"

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

    def __hash__(self) -> int:
        return hash(self._key())

    def __lt__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        if self.name != other.name:
            return NotImplemented
        return self._cmp(other) < 0

    def __le__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        if self.name != other.name:
            return NotImplemented
        return self._cmp(other) <= 0

    def __eq__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return self.name == other.name and self._cmp(other) == 0

    def __ne__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return self.name != other.name or self._cmp(other) != 0

    def __ge__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        if self.name != other.name:
            return NotImplemented
        return self._cmp(other) >= 0

    def __gt__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        if self.name != other.name:
            return NotImplemented
        return self._cmp(other) > 0

    @formatted
    def __repr__(self) -> str:
        return (
            f"NEVR(name={self.name!r}, epoch={self.epoch!r}, "
            f"version={self.version!r}, release={self.release!r})"
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

    def __hash__(self) -> int:
        return hash(self._key())

    def __lt__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        if self.name != other.name or self.arch != other.arch:
            return NotImplemented
        return self._cmp(other) < 0

    def __le__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        if self.name != other.name or self.arch != other.arch:
            return NotImplemented
        return self._cmp(other) <= 0

    def __eq__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return (
            self.name == other.name
            and self.arch == other.arch
            and self._cmp(other) == 0
        )

    def __ne__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        return (
            self.name != other.name or self.arch != other.arch or self._cmp(other) != 0
        )

    def __ge__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        if self.name != other.name or self.arch != other.arch:
            return NotImplemented
        return self._cmp(other) >= 0

    def __gt__(self, other: object) -> bool:
        if type(other) is not self.__class__:
            return NotImplemented
        if self.name != other.name or self.arch != other.arch:
            return NotImplemented
        return self._cmp(other) > 0

    @formatted
    def __repr__(self) -> str:
        return (
            f"NEVRA(name={self.name!r}, epoch={self.epoch!r}, "
            f"version={self.version!r}, release={self.release!r}, "
            f"arch={self.arch!r})"
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


def count_brackets(string: str) -> Tuple[int, int]:
    """
    Counts non-pair brackets in %{...} and %(...) expressions appearing in the given string.

    Args:
        string: Input string.

    Returns:
        The count of non-pair curly braces and the count of non-pair parentheses.
    """
    bc = pc = 0
    chars = list(string)
    while chars:
        c = chars.pop(0)
        if c == "\\" and chars:
            chars.pop(0)
            continue
        if c == "%" and chars:
            c = chars.pop(0)
            if c == "{":
                bc += 1
            elif c == "(":
                pc += 1
            continue
        if c == "{" and bc > 0:
            bc += 1
            continue
        if c == "}" and bc > 0:
            bc -= 1
            continue
        if c == "(" and pc > 0:
            pc += 1
            continue
        if c == ")" and pc > 0:
            pc -= 1
            continue
    return bc, pc


def split_conditional_macro_expansion(value: str) -> Tuple[str, str, str]:
    """
    Splits conditional macro expansion into its body and prefix and suffix of it.
    If the passed string isn't a conditional macro expansion, returns it as it is.

    Args:
        value: String to be split.

    Returns:
        Tuple of body, prefix, suffix. Prefix and suffix will be empty if the passed string
        isn't a conditional macro expansion.
    """
    try:
        nodes = ValueParser.parse(value)
    except UnterminatedMacroException:
        return value, "", ""
    if len(nodes) != 1:
        return value, "", ""
    node = nodes[0]
    if not isinstance(node, ConditionalMacroExpansion):
        return value, "", ""
    return "".join(str(n) for n in node.body), f"%{{{node.prefix}{node.name}:", "}"


# Python 3.6-3.8 do not allow creating a generic UserList at runtime.
# This hack allows type checkers to determine the UserList dunder method return
# types while still working at runtime.
if TYPE_CHECKING or sys.version_info >= (3, 9):
    UserList = collections.UserList
else:
    # UserList[...] always returns a UserList
    UserList = collections.defaultdict(lambda: collections.UserList)
