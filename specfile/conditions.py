# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import re
from typing import TYPE_CHECKING, List, Optional, Tuple

from specfile.exceptions import RPMException
from specfile.macros import Macros

if TYPE_CHECKING:
    from specfile.macro_definitions import MacroDefinitions
    from specfile.specfile import Specfile


def resolve_expression(
    keyword: str, expression: str, context: Optional["Specfile"] = None
) -> bool:
    """
    Resolves a RPM expression.

    Args:
        keyword: Condition keyword, e.g. _%if_ or _%ifarch_.
        expression: Expression string or a whitespace-delimited list
            of arches/OSes in case keyword is a variant of _%ifarch_/_%ifos_.
        context: `Specfile` instance that defines the context for macro expansions.

    Returns:
        Resolved expression as a boolean value.
    """

    def expand(s):
        if not context:
            return Macros.expand(s)
        result = context.expand(s, skip_parsing=getattr(expand, "skip_parsing", False))
        # parse only once
        expand.skip_parsing = True
        return result

    if keyword in ("%if", "%elif"):
        try:
            result = expand(f"%{{expr:{expression}}}")
        except RPMException:
            return False
        if result.startswith("%{expr:"):
            # the expansion silently failed
            return False
        try:
            return int(result) != 0
        except ValueError:
            return True
    elif keyword.endswith("arch"):
        target_cpu = expand("%{_target_cpu}")
        match = any(t for t in expand(expression).split() if t == target_cpu)
        return not match if keyword == "%ifnarch" else match
    elif keyword.endswith("os"):
        target_os = expand("%{_target_os}")
        match = any(t for t in expand(expression).split() if t == target_os)
        return not match if keyword == "%ifnos" else match
    return False


def process_conditions(
    lines: List[str],
    macro_definitions: Optional["MacroDefinitions"] = None,
    context: Optional["Specfile"] = None,
) -> List[Tuple[str, bool]]:
    """
    Processes conditions in a spec file. Takes a list of lines and returns the same
    list of lines extended with information about their validity. A line is considered
    valid if it doesn't appear in a false branch of any condition.

    Args:
        lines: List of lines in a spec file.
        macro_definitions: Parsed macro definitions to be used to prevent parsing conditions
            inside their bodies (and most likely failing).
        context: `Specfile` instance that defines the context for macro expansions.

    Returns:
        List of tuples in the form of (line, validity).
    """

    def expand(s):
        if not context:
            return Macros.expand(s)
        result = context.expand(s, skip_parsing=getattr(expand, "skip_parsing", False))
        # parse only once
        expand.skip_parsing = True
        return result

    excluded_lines = []
    if macro_definitions:
        for md in macro_definitions:
            position = md.get_position(macro_definitions)
            excluded_lines.append(range(position, position + len(md.body.split("\n"))))
    condition_regex = re.compile(
        r"""
        ^
        \s*                                           # optional preceding whitespace
        (?P<kwd>%((el)?if(n?(arch|os))?|endif|else))  # keyword
        \s*
        (
            \s+
            (?P<expr>.*?)                             # expression
            (?P<end>\s*|\\)                           # optional following whitespace
                                                      # or a backslash indicating
                                                      # that the expression continues
                                                      # on the next line
        )?
        $
        """,
        re.VERBOSE,
    )
    result = []
    branches = [True]
    indexed_lines = list(enumerate(lines))
    while indexed_lines:
        index, line = indexed_lines.pop(0)
        # ignore conditions inside macro definition body
        if any(index in r for r in excluded_lines):
            result.append((line, branches[-1]))
            continue
        try:
            expanded_line = expand(line)
        except RPMException:
            # ignore failed expansion and use the original line
            expanded_line = line
        m = condition_regex.match(expanded_line)
        if not m:
            result.append((line, branches[-1]))
            continue
        keyword = m.group("kwd")
        if keyword == "%endif":
            result.append((line, branches[-2]))
            branches.pop()
        elif keyword.startswith("%el"):
            result.append((line, branches[-2]))
            if branches[-2]:
                branches[-1] = not branches[-1]
        else:
            result.append((line, branches[-1]))
        if keyword.startswith("%if") or keyword.startswith("%elif"):
            expression = m.group("expr")
            if expression:
                if m.group("end") == "\\":
                    expression += "\\"
                while expression.endswith("\\") and indexed_lines:
                    _, line = indexed_lines.pop(0)
                    result.append((line, branches[-1]))
                    expression = expression[:-1] + line
            branch = (
                False
                if not branches[-1]
                else resolve_expression(keyword, expression or "0", context)
            )
            if keyword.startswith("%el"):
                branches[-1] = branch
            else:
                branches.append(branch)
    return result
