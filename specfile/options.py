# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import re
import string
from enum import Enum, auto
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Union, overload

from specfile.exceptions import OptionsException
from specfile.formatter import formatted
from specfile.value_parser import StringLiteral, ValueParser


class TokenType(Enum):
    DEFAULT = auto()
    WHITESPACE = auto()
    QUOTED = auto()
    DOUBLE_QUOTED = auto()


class Token(collections.abc.Hashable):
    """
    Class that represents a single token in an option string.

    Attributes:
        type: Token type.
        value: Token value.
    """

    def __init__(self, type: TokenType, value: str) -> None:
        self.type = type
        self.value = value

    @formatted
    def __repr__(self) -> str:
        return f"Token({self.type!r}, {self.value!r})"

    def __str__(self) -> str:
        if self.type == TokenType.WHITESPACE:
            return self.value
        elif self.type == TokenType.QUOTED:
            # escape single quotes
            value = self.value.replace("'", r"\'")
            return f"'{value}'"
        elif self.type == TokenType.DOUBLE_QUOTED:
            # escape double quotes
            value = self.value.replace('"', r"\"")
            return f'"{value}"'
        # escape quotes and whitespace
        return re.sub(r"['\"\s]", r"\\\g<0>", self.value)

    def _key(self) -> tuple:
        return self.type, self.value

    def __hash__(self) -> int:
        return hash(self._key())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Token):
            return NotImplemented
        return self._key() == other._key()


class Positionals(collections.abc.MutableSequence):
    """Class that represents a sequence of positional arguments."""

    def __init__(self, options: "Options") -> None:
        """
        Initializes a positionals object.

        Args:
            options: `Options` instance this object is tied with.
        """
        self._options = options

    @formatted
    def __repr__(self) -> str:
        return f"Positionals({self._options!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Positionals, list)):
            return NotImplemented
        return list(self) == other

    def __len__(self) -> int:
        return len(self._get_items())

    @overload
    def __getitem__(self, i: int) -> Union[int, str]:
        pass

    @overload
    def __getitem__(self, i: slice) -> List[Union[int, str]]:
        pass

    def __getitem__(self, i):
        items = self._get_items()
        if isinstance(i, slice):
            result = []
            for index in items[i]:
                value = self._options._tokens[index].value
                result.append(int(value) if value.isnumeric() else value)
            return result
        else:
            value = self._options._tokens[items[i]].value
            return int(value) if value.isnumeric() else value

    @overload
    def __setitem__(self, i: int, item: Union[int, str]) -> None:
        pass

    @overload
    def __setitem__(self, i: slice, item: Iterable[Union[int, str]]) -> None:
        pass

    def __setitem__(self, i, item):
        items = self._get_items()
        if isinstance(i, slice):
            for i0, i1 in enumerate(range(len(items))[i]):
                self._options._tokens[items[i1]].value = str(item[i0])
        else:
            self._options._tokens[items[i]].value = str(item)

    def __delitem__(self, i: Union[int, slice]) -> None:
        def delete(index):
            tokens = self._options._tokens
            if index == 0:
                if len(tokens) > 1 and tokens[1].type == TokenType.WHITESPACE:
                    del tokens[1]
            else:
                if tokens[index - 1].type == TokenType.WHITESPACE:
                    index -= 1
                    del tokens[index]
            del tokens[index]

        items = self._get_items()
        if isinstance(i, slice):
            for index in reversed(items[i]):
                delete(index)
        else:
            delete(items[i])

    def _get_items(self) -> List[int]:
        """
        Gets all positional arguments.

        Returns:
            List of indices of tokens that are positional arguments.
        """
        result = []
        i = 0
        while i < len(self._options._tokens):
            if self._options._tokens[i].type == TokenType.WHITESPACE:
                i += 1
                continue
            # exclude options (starting with -) and their arguments (if any)
            value = self._options._tokens[i].value
            if value.startswith("-"):
                i += 1
                if len(value) > 1:
                    if value[1] in self._options.optstring.replace(":", ""):
                        if self._options._requires_argument(value[1]):
                            if len(value) == 2:
                                if (
                                    i < len(self._options._tokens)
                                    and self._options._tokens[i].type
                                    == TokenType.WHITESPACE
                                ):
                                    i += 1
                                i += 1
                continue
            result.append(i)
            i += 1
        return result

    def insert(self, i: int, value: Union[int, str]) -> None:
        """
        Inserts a new positional argument at the specified index.

        Args:
            i: Requested index.
            value: Value of the positional argument.
        """
        items = self._get_items()
        if i > len(items):
            i = len(items)
        if items and i < len(items):
            index = items[i]
            if index > 0:
                if self._options._tokens[index - 1].type == TokenType.WHITESPACE:
                    index -= 1
        else:
            index = len(self._options._tokens)
        self._options._tokens.insert(
            index,
            Token(
                (
                    TokenType.DOUBLE_QUOTED
                    if self._options._needs_quoting(value)
                    else TokenType.DEFAULT
                ),
                str(value),
            ),
        )
        if index > 0:
            self._options._tokens.insert(index, Token(TokenType.WHITESPACE, " "))


class Options(collections.abc.MutableMapping):
    """
    Class that represents macro options.

    Attributes:
        optstring: getopt-like option string containing recognized option characters.
            Option characters are ASCII letters, upper or lower-case.
            If such a character is followed by a colon, the option
            requires an argument.
        defaults: Dict specifying default arguments to options.
    """

    def __init__(
        self,
        tokens: List[Token],
        optstring: Optional[str] = None,
        defaults: Optional[Dict[str, Union[bool, int, str]]] = None,
    ) -> None:
        """
        Initializes an options object.

        Args:
            tokens: List of tokens in an option string.
            optstring: String containing recognized option characters.
                Option characters are ASCII letters, upper or lower-case.
                If such a character is followed by a colon, the option
                requires an argument.
            defaults: Dict specifying default arguments to options.
        """
        self._tokens = tokens.copy()
        self.optstring = optstring or ""
        self.defaults = defaults.copy() if defaults is not None else {}

    @formatted
    def __repr__(self) -> str:
        return f"Options({self._tokens!r}, {self.optstring!r}, {self.defaults!r})"

    def __str__(self) -> str:
        return "".join(str(t) for t in self._tokens)

    def _valid_option(self, name: str) -> bool:
        """
        Determines if a name represents a recognized option.

        Args:
            name: Name of the option.

        Returns:
            `True` if the option is recognized, otherwise `False`.
        """
        try:
            # use parent's __getattribute__() so this method can be called from __getattr__()
            optstring = super().__getattribute__("optstring")
        except AttributeError:
            return False
        return name in optstring.replace(":", "")

    def _requires_argument(self, option: str) -> bool:
        """
        Determines if an option requires an argument.

        Args:
            option: Name of the option.

        Returns:
            `True` if the option requires an argument, otherwise `False`.

        Raises:
            ValueError: If the specified option is not valid.
        """
        i = self.optstring.index(option) + 1
        return i < len(self.optstring) and self.optstring[i] == ":"

    def _find_option(self, name: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Searches for an option in tokens of an option string.

        Args:
            name: Name of the option.

        Returns:
            Tuple of indices where the first is the index of a token matching
            the option and the second is the index of a token matching
            its argument, or `None` if there is no match.
        """
        option = f"-{name}"
        for i, token in reversed(list(enumerate(self._tokens))):
            if not token.value.startswith(option):
                continue
            if token.value != option:
                return i, i
            if not self._requires_argument(name):
                return i, None
            j = i + 1
            if j == len(self._tokens):
                return i, None
            if self._tokens[j].type == TokenType.WHITESPACE:
                j += 1
            if j == len(self._tokens):
                return i, None
            if self._tokens[j].value.startswith("-"):
                return i, None
            return i, j
        return None, None

    @staticmethod
    def _needs_quoting(value):
        # if there is a whitespace, enquote the value rather than escaping it
        return any(ws in str(value) for ws in string.whitespace)

    def __getattr__(self, name: str) -> Optional[Union[bool, int, str]]:
        if not self._valid_option(name):
            return super().__getattribute__(name)
        i, j = self._find_option(name)
        if i is None:
            if self._requires_argument(name):
                return self.defaults.get(name)
            return False
        value = (
            self._tokens[j].value
            if j is not None and j > i
            else self._tokens[i].value[2:]
        )
        if not value:
            return True
        if value.isnumeric():
            return int(value)
        return value

    def __setattr__(self, name: str, value: Union[bool, int, str]) -> None:
        if not self._valid_option(name):
            return super().__setattr__(name, value)
        if self._requires_argument(name) and isinstance(value, bool):
            raise OptionsException(f"Option -{name} requires an argument.")
        if (
            not self._requires_argument(name)
            and not isinstance(value, bool)
            and value is not None
        ):
            raise OptionsException(f"Option -{name} is a flag.")
        i, j = self._find_option(name)
        if i is None:
            if value is not None and value is not False:
                if self._tokens:
                    self._tokens.append(Token(TokenType.WHITESPACE, " "))
                if value is True:
                    self._tokens.append(Token(TokenType.DEFAULT, f"-{name}"))
                elif isinstance(value, int):
                    self._tokens.append(Token(TokenType.DEFAULT, f"-{name}{value}"))
                else:
                    self._tokens.append(Token(TokenType.DEFAULT, f"-{name}"))
                    self._tokens.append(Token(TokenType.WHITESPACE, " "))
                    self._tokens.append(
                        Token(
                            (
                                TokenType.DOUBLE_QUOTED
                                if self._needs_quoting(value)
                                else TokenType.DEFAULT
                            ),
                            value,
                        )
                    )
            return
        if value is None or value is False:
            return delattr(self, name)
        if j is not None and j > i:
            if self._needs_quoting(value):
                if self._tokens[j].type not in (
                    TokenType.QUOTED,
                    TokenType.DOUBLE_QUOTED,
                ):
                    self._tokens[j].type = TokenType.DOUBLE_QUOTED
            else:
                self._tokens[j].type = TokenType.DEFAULT
            self._tokens[j].value = str(value)
        else:
            if self._needs_quoting(value):
                self._tokens[i].value = self._tokens[i].value[:2]
                self._tokens.insert(i + 1, Token(TokenType.DOUBLE_QUOTED, str(value)))
                self._tokens.insert(i + 1, Token(TokenType.WHITESPACE, " "))
            else:
                self._tokens[i].value = self._tokens[i].value[:2] + str(value)

    def __delattr__(self, name: str) -> None:
        if not self._valid_option(name):
            return super().__delattr__(name)
        i, j = self._find_option(name)
        if i is None:
            return
        if i == 0:
            if (
                j is not None
                and j + 1 < len(self._tokens)
                and self._tokens[j + 1].type == TokenType.WHITESPACE
            ):
                j += 1
        elif self._tokens[i - 1].type == TokenType.WHITESPACE:
            i -= 1
        if j is not None and j > i:
            del self._tokens[i : j + 1]
        else:
            del self._tokens[i]

    def __len__(self) -> int:
        return len(
            {
                t.value[1]
                for t in self._tokens
                if t.type != TokenType.WHITESPACE
                and t.value.startswith("-")
                and len(t.value) > 1
                and t.value[1] in self.optstring.replace(":", "")
            }
        )

    def __getitem__(self, key: str) -> Union[bool, int, str]:
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key: str, item: Union[bool, int, str]) -> None:
        try:
            return setattr(self, key, item)
        except AttributeError:
            raise KeyError(key)

    def __delitem__(self, key: str) -> None:
        try:
            return delattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        for option in self.optstring.replace(":", ""):
            i, _ = self._find_option(option)
            if i is not None:
                yield option

    @property
    def positional(self) -> Positionals:
        """Sequence of positional arguments."""
        return Positionals(self)

    @positional.setter
    def positional(self, value: List[Union[int, str]]) -> None:
        positionals = Positionals(self)
        positionals.clear()
        positionals.extend(value)

    @staticmethod
    def tokenize(option_string: str) -> List[Token]:
        """
        Tokenizes an option string.

        Follows the same rules as `poptParseArgvString()` that is used by RPM.

        Args:
            option_string: Option string.

        Returns:
            List of tokens.

        Raises:
            OptionsException: If the option string is untokenizable.
        """
        result: List[Token] = []
        token = ""
        quote = None
        inp = []
        for node in ValueParser.parse(option_string):
            if isinstance(node, StringLiteral):
                inp.extend(list(str(node)))
                continue
            inp.append(str(node))
        while inp:
            c = inp.pop(0)
            if c == quote:
                if token:
                    result.append(
                        Token(
                            (
                                TokenType.QUOTED
                                if quote == "'"
                                else TokenType.DOUBLE_QUOTED
                            ),
                            token,
                        )
                    )
                    token = ""
                quote = None
                continue
            if quote:
                if c == "\\":
                    if not inp:
                        raise OptionsException("No escaped character")
                    c = inp.pop(0)
                    if c != quote:
                        token += "\\"
                token += c
                continue
            if c.isspace():
                if token:
                    result.append(Token(TokenType.DEFAULT, token))
                    token = ""
                whitespace = c
                while inp:
                    c = inp.pop(0)
                    if not c.isspace():
                        break
                    whitespace += c
                else:
                    result.append(Token(TokenType.WHITESPACE, whitespace))
                    break
                inp.insert(0, c)
                result.append(Token(TokenType.WHITESPACE, whitespace))
                continue
            if c in ('"', "'"):
                if token:
                    result.append(Token(TokenType.DEFAULT, token))
                    token = ""
                quote = c
                continue
            if c == "\\":
                if not inp:
                    raise OptionsException("No escaped character")
                c = inp.pop(0)
            token += c
        if quote:
            raise OptionsException("No closing quotation")
        if token:
            result.append(Token(TokenType.DEFAULT, token))
        return result
