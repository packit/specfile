# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import itertools
import re
from abc import ABC
from string import Template
from typing import TYPE_CHECKING, Generator, List, Optional, Pattern, Set, Tuple

from specfile.exceptions import UnterminatedMacroException
from specfile.formatter import formatted
from specfile.macros import Macros

if TYPE_CHECKING:
    from specfile.specfile import Specfile

SUBSTITUTION_GROUP_PREFIX = "sub_"


class Node(ABC):
    """Base class for all nodes."""

    ...


class StringLiteral(Node):
    """Node representing string literal."""

    def __init__(self, value: str) -> None:
        self.value = value

    @formatted
    def __repr__(self) -> str:
        return f"StringLiteral({self.value!r})"

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.value == other.value


class ShellExpansion(Node):
    """Node representing shell expansion, e.g. _%(whoami)_."""

    def __init__(self, body: str) -> None:
        self.body = body

    @formatted
    def __repr__(self) -> str:
        # determine class name dynamically so that inherited classes
        # don't have to reimplement __repr__()
        return f"{self.__class__.__name__}({self.body!r})"

    def __str__(self) -> str:
        return f"%({self.body})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.body == other.body


class ExpressionExpansion(ShellExpansion):
    """Node representing expression expansion, e.g. _%[1+1]_."""

    def __str__(self) -> str:
        return f"%[{self.body}]"


class MacroSubstitution(Node):
    """Node representing macro substitution, e.g. _%version_."""

    def __init__(self, body: str) -> None:
        tokens = re.split(r"^([?!]*)", body, maxsplit=1)
        if len(tokens) == 1:
            self.prefix, self.name = "", tokens[0]
        else:
            _, self.prefix, self.name = tokens

    @formatted
    def __repr__(self) -> str:
        return f"MacroSubstitution({(self.prefix + self.name)!r})"

    def __str__(self) -> str:
        return f"%{self.prefix}{self.name}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.prefix == other.prefix and self.name == other.name


class EnclosedMacroSubstitution(Node):
    """Node representing macro substitution enclosed in brackets, e.g. _%{?dist}_."""

    def __init__(self, body: str) -> None:
        tokens = re.split(r"^([?!]*)", body, maxsplit=1)
        if len(tokens) == 1:
            self.prefix, rest = "", tokens[0]
        else:
            _, self.prefix, rest = tokens
        self.name: str
        self.args: List[str]
        self.name, *self.args = rest.split()

    @formatted
    def __repr__(self) -> str:
        args = (" " + " ".join(self.args)) if self.args else ""
        return f"EnclosedMacroSubstitution({(self.prefix + self.name + args)!r})"

    def __str__(self) -> str:
        args = (" " + " ".join(self.args)) if self.args else ""
        return f"%{{{self.prefix}{self.name}{args}}}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (
            self.prefix == other.prefix
            and self.name == other.name
            and self.args == other.args
        )


class ConditionalMacroExpansion(Node):
    """Node representing conditional macro expansion, e.g. _%{?prerel:0.}_."""

    def __init__(self, condition: str, body: List[Node]) -> None:
        tokens = re.split(r"^([?!]*)", condition, maxsplit=1)
        if len(tokens) == 1:
            self.prefix, self.name = "", tokens[0]
        else:
            _, self.prefix, self.name = tokens
        self.body = body

    @formatted
    def __repr__(self) -> str:
        return (
            f"ConditionalMacroExpansion({(self.prefix + self.name)!r}, {self.body!r})"
        )

    def __str__(self) -> str:
        body = "".join(str(n) for n in self.body)
        return f"%{{{self.prefix}{self.name}:{body}}}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (
            self.prefix == other.prefix
            and self.name == other.name
            and self.body == other.body
        )


class BuiltinMacro(Node):
    """Node representing built-in macro, e.g. _%{quote:Ancient Greek}_."""

    def __init__(self, name: str, body: str) -> None:
        self.name = name
        self.body = body

    @formatted
    def __repr__(self) -> str:
        return f"BuiltinMacro({self.name!r}, {self.body!r})"

    def __str__(self) -> str:
        return f"%{{{self.name}:{self.body}}}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.name == other.name and self.body == other.body


class ValueParser:
    @classmethod
    def flatten(cls, nodes: List[Node]) -> Generator[Node, None, None]:
        """
        Generator that yields flattened nodes. Conditional macro expansions are treated
        as if their conditions were true and their bodies are flattened.

        Args:
            nodes: List of nodes to be flattened.

        Yields:
            Individual nodes.
        """
        for node in nodes:
            if isinstance(node, ConditionalMacroExpansion):
                yield from cls.flatten(node.body)
            else:
                yield node

    @classmethod
    def parse(cls, value: str) -> List[Node]:
        """
        Parses a value into a list of nodes.

        Follows the parsing logic of `expandMacro()` from _rpm/rpmio/macro.c_ in RPM source.

        Args:
            value: Value string to parse.

        Returns:
            Parsed value as a list of nodes.

        Raises:
            UnterminatedMacroException: If there is a macro that doesn't end.
        """
        pairs = {"(": ")", "{": "}", "[": "]"}

        def find_matching_parenthesis(index):
            level = 0
            for i in range(index, len(value)):
                if value[i] == "\\":
                    continue
                elif value[i] == pairs[value[index]]:
                    level -= 1
                    if level <= 0:
                        return i + 1
                elif value[i] == value[index]:
                    level += 1
            return None

        def find_macro_end(index):
            i = index
            if value[i] in pairs.keys():
                return find_matching_parenthesis(i)
            while i < len(value) and value[i] in "?!":
                i += 1
            if i < len(value) and value[i] == "-":
                i += 1
            while i < len(value) and (value[i].isalnum() or value[i] == "_"):
                i += 1
            if i + 1 < len(value) and value[i : i + 1] == "**":
                i += 2
            elif i < len(value) and value[i] in "*#":
                i += 1
            return i

        result: List[Node] = []
        start = 0
        offset = 0
        while start < len(value):
            try:
                end = value.index("%", start + offset)
                try:
                    if value[end + 1] == "%":
                        offset = end + 2
                        continue
                except IndexError:
                    raise UnterminatedMacroException
            except ValueError:
                end = None
            if end is None:
                break
            if end > start:
                result.append(StringLiteral(value[start:end]))
            start = end
            end = find_macro_end(start + 1)
            if end is None:
                raise UnterminatedMacroException
            if value[start + 1] == "(":
                result.append(ShellExpansion(value[start + 2 : end - 1]))
            elif value[start + 1] == "[":
                result.append(ExpressionExpansion(value[start + 2 : end - 1]))
            elif value[start + 1] == "{":
                if ":" in value[start:end]:
                    condition, body = value[start + 2 : end - 1].split(":", maxsplit=1)
                    tokens = re.split(r"^([?!]*)", condition, maxsplit=1)
                    prefix = tokens[0 if len(tokens) == 1 else 1]
                    if "?" in prefix:
                        result.append(
                            ConditionalMacroExpansion(condition, cls.parse(body))
                        )
                    else:
                        result.append(BuiltinMacro(condition, body))
                else:
                    result.append(EnclosedMacroSubstitution(value[start + 2 : end - 1]))
            else:
                result.append(MacroSubstitution(value[start + 1 : end]))
            start = end
            offset = 0
        if value[start:]:
            result.append(StringLiteral(value[start:]))
        return result

    @classmethod
    def construct_regex(
        cls,
        value: str,
        modifiable_entities: Set[str],
        flippable_entities: Set[str],
        context: Optional["Specfile"] = None,
    ) -> Tuple[Pattern, Template, Set[str]]:
        """
        Parses the given value and constructs a regex that allows matching
        substrings of a different, but similar value to macro substitutions
        representing modifiable entities, and to modifiable substrings
        of the original value.
        Also constructs a corresponding template that allows updating
        the original value.

        For example, for nodes representing the string "1.%{version_minor}", assuming
        "version_minor" is a local macro definition (thus a modifiable entity),
        the resulting regex would be "^(?P<sub_0>)\\.(?P<version_minor>.+?)$",
        and the corresponding template would be "${sub_0}.%{version_minor}".
        If a requested new value would be a match to this regex, the "version_minor"
        macro definition could be modified with the matching substring and the final
        value could be determined by performing a substitution on the template
        with groupdict of the match.

        Args:
            value: Value string to parse.
            modifiable_entities: Names of modifiable entities, i.e. local macro definitions
                and tags.
            flippable_entities: Names of entities that can be enabled/disabled,
                i.e. macro definitions. Must be a subset of modifiable_entities.
            context: `Specfile` instance that defines the context for macro expansions.

        Returns:
            Tuple in the form of (constructed regex, corresponding template, entities to flip).
        """

        def expand(s):
            if context:
                result = context.expand(
                    s, skip_parsing=getattr(expand, "skip_parsing", False)
                )
                # parse only once
                expand.skip_parsing = True
                return result
            return Macros.expand(s)

        processed_entities = set()
        entities_to_flip = set()

        def flatten(nodes):
            # get rid of conditional macro expansions

            def evaluate(node):
                if node.name not in modifiable_entities:
                    return False
                negative_check = node.prefix.count("!") % 2 > 0
                defined = expand(f"%{{?{node.name}:1}}")
                if negative_check and defined or not (negative_check or defined):
                    if node.name not in flippable_entities:
                        return False
                    if (
                        node.name in processed_entities
                        and node.name not in entities_to_flip
                    ):
                        # it's not possible to flip this one because it was
                        # already processed without flipping
                        return False
                    entities_to_flip.add(node.name)
                elif node.name in entities_to_flip:
                    # this one was flipped earlier, so we can't continue
                    # without flipping
                    return False
                processed_entities.add(node.name)
                return True

            result = []
            for node in nodes:
                if isinstance(node, ConditionalMacroExpansion):
                    if evaluate(node):
                        result.append(f"%{{{node.prefix}{node.name}:")
                        result.extend(flatten(node.body))
                        result.append("}")
                    else:
                        result.append(str(node))
                else:
                    result.append(node)
            return result

        nodes = cls.parse(value)

        # convert nodes into constant, variable and group tokens
        tokens = []
        for node in flatten(nodes):
            if isinstance(node, str):
                tokens.append(("c", "", node))
            elif isinstance(node, StringLiteral):
                tokens.append(("v", node.value, ""))
            elif isinstance(node, (ShellExpansion, ExpressionExpansion, BuiltinMacro)):
                const = expand(str(node))
                tokens.append(("c", const, str(node)))
            elif isinstance(node, MacroSubstitution):
                if node.prefix.count("!") % 2 == 0 and node.name in modifiable_entities:
                    tokens.append(("g", node.name, str(node)))
                else:
                    const = expand(str(node))
                    tokens.append(("c", const, str(node)))
            elif isinstance(node, EnclosedMacroSubstitution):
                if (
                    node.prefix.count("!") % 2 == 0
                    and not node.args
                    and node.name in modifiable_entities
                ):
                    tokens.append(("g", node.name, str(node)))
                else:
                    const = expand(str(node))
                    tokens.append(("c", const, str(node)))

        def escape(s):
            return s.replace("$", "$$")

        # squash constants and variables
        _tokens = []
        for key, grp in itertools.groupby(tokens, lambda x: x[0]):
            if key in ("c", "v"):
                regex = template = ""
                for _, r, t in grp:
                    regex += r
                    template += t
                _tokens.append((key, regex, template))
            else:
                groups = list(grp)
                if len(groups) > 1:
                    # there are unseparated groups, reliable match is impossible
                    return re.compile("^$"), Template(escape(value)), set()
                _tokens.extend(groups)
        tokens = _tokens

        def is_group_nearby(tokens, index, after):
            for token in tokens[index + 1 :] if after else reversed(tokens[:index]):
                if token[0] == "c":
                    # skip empty constants
                    if token[1]:
                        return False
                elif token[0] == "g":
                    return True
                elif token[0] == "v":
                    return False
            return False

        # construct regex and template
        regex = "^"
        template = ""
        named_groups = []
        sub = 0
        for i, token in enumerate(tokens):
            if token[0] == "c":
                regex += re.escape(token[1])
                template += escape(token[2])
            elif token[0] == "g":
                group = token[1]
                if group in named_groups:
                    # this group name already exists, make a backreference
                    regex += f"(?P={group})"
                else:
                    regex += f"(?P<{group}>.+)"
                    named_groups.append(group)
                template += escape(token[2])
            elif token[0] == "v":
                value = token[1]
                # make sure there is at least one constant character between groups
                var_regex = "^"
                if is_group_nearby(tokens, i, False):
                    var_regex += r"(?P<prefix>\w*[^\w])"
                var_regex += "(?P<value>.*)"
                if is_group_nearby(tokens, i, True):
                    var_regex += r"(?P<suffix>[^\w]\w*)"
                var_regex += "$"
                m = re.match(var_regex, value)
                if not m:
                    regex += re.escape(value)
                    template += escape(value)
                    continue
                d = m.groupdict()
                prefix = d.get("prefix", "")
                value = d.get("value", "")
                suffix = d.get("suffix", "")
                regex += re.escape(prefix)
                template += escape(prefix)
                if value:
                    # make a substitution group
                    group = f"{SUBSTITUTION_GROUP_PREFIX}{sub}"
                    regex += f"(?P<{group}>.+?)"
                    template += f"${{{group}}}"
                    named_groups.append(group)
                    sub += 1
                regex += re.escape(suffix)
                template += escape(suffix)
        regex += "$"
        return re.compile(regex), Template(template), entities_to_flip
