# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import ast
import functools
from typing import Callable

from specfile.exceptions import SpecfileException


def format_expression(expression: str, line_length_threshold: int = 80) -> str:
    """
    Formats the specified Python expression.

    Only supports a small subset of Python AST that should be sufficient for use in __repr__().

    Args:
        expression: Python expression to reformat.
        line_length_threshold: Threshold for line lengths. It's not a hard limit,
          it can be exceeded in some cases.

    Returns:
        Formatted expression.

    Raises:
        SyntaxError if the expression is not parseable.
        SpecfileException if there is an unsupported AST node in the expression.
    """

    def fmt(node, indent=0, prefix="", multiline=False):
        result = " " * indent + prefix
        if isinstance(node, ast.Constant):
            result += repr(node.value)
        elif isinstance(node, (ast.Tuple, ast.List, ast.Dict, ast.Call)):
            if isinstance(node, ast.Tuple):
                start, end = "(", ")" if multiline or len(node.elts) != 1 else ",)"
                items = [(None, e) for e in node.elts]
                delimiter = None
            elif isinstance(node, ast.List):
                start, end = "[", "]"
                items = [(None, e) for e in node.elts]
                delimiter = None
            elif isinstance(node, ast.Dict):
                start, end = "{", "}"
                items = [(fmt(k, 0), v) for k, v in zip(node.keys, node.values)]
                delimiter = ": "
            elif isinstance(node, ast.Call):
                start, end = f"{node.func.id}(", ")"
                items = [(None, a) for a in node.args] + [
                    (kw.arg, kw.value) for kw in node.keywords
                ]
                delimiter = "="
            result += start
            if multiline:
                result += "\n"
            while items:
                key, value = items.pop(0)
                result += fmt(
                    value,
                    indent + 4 if multiline else 0,
                    f"{key}{delimiter}" if key else "",
                )
                if multiline:
                    result += ",\n"
                elif items:
                    result += ", "
            if multiline:
                result += " " * indent
            result += end
        else:
            raise SpecfileException(
                f"Unsupported AST node: ast.{node.__class__.__name__}"
            )
        if not multiline and len(result) > line_length_threshold:
            result = fmt(node, indent, prefix, True)
        return result

    def find_matching_bracket(value, index):
        level = 0
        for i in range(index, len(value)):
            if value[i] == ">":
                level -= 1
                if level <= 0:
                    return i + 1
            elif value[i] == "<":
                level += 1
        return None

    placeholders = []
    while True:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            # some objects (e.g. enums) are not represented by a valid expression,
            # replace their representation with placeholders
            # (assume such a representation is enclosed in <> and doesn't spawn
            # across multiple lines)
            lines = expression.splitlines()
            if not e.lineno or not e.offset:
                raise
            if lines[e.lineno - 1][e.offset - 1] != "<":
                raise
            index = find_matching_bracket(lines[e.lineno - 1], e.offset - 1)
            if not index:
                raise
            value = lines[e.lineno - 1][e.offset - 1 : index]
            # convert the value to a string literal
            placeholder = repr(value)
            placeholders.append((placeholder, value))
            lines[e.lineno - 1] = (
                lines[e.lineno - 1][: e.offset - 1]
                + placeholder
                + lines[e.lineno - 1][index:]
            )
            expression = "\n".join(lines)
        else:
            break
    result = fmt(tree.body)
    # revert placeholders
    for placeholder, value in placeholders:
        result = result.replace(placeholder, value, 1)
    return result


def formatted(function: Callable[..., str]) -> Callable[..., str]:
    """Decorator for formatting the output of __repr__()."""

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        result = function(*args, **kwargs)
        try:
            return format_expression(result)
        except (SyntaxError, SpecfileException):
            return result

    return wrapper
