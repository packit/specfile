#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import List

import click
from pyparsing import (
    Combine,
    Group,
    Literal,
    ParserElement,
    Suppress,
    Word,
    c_style_comment,
    dbl_quoted_string,
    delimited_list,
    pyparsing_common,
    remove_quotes,
    srange,
)

# automatically suppress all string literals
ParserElement.inline_literals_using(Suppress)


def extract_sections(filename: Path) -> List[str]:
    """
    Extracts section names from a constant array looking like this:

    static const struct PartRec {
        int part;
        int prebuildonly;
        size_t len;
        const char * token;
    } partList[] = {
        { PART_PREAMBLE,      0, LEN_AND_STR("%package")},
        { PART_PREP,          1, LEN_AND_STR("%prep")},
        ...
        {0, 0, 0}
    };

    Args:
        filename: Path to the file to extract sections from.

    Returns:
        List of section names.
    """
    constant = Word(srange("[A-Z_]")).suppress()
    name = dbl_quoted_string.set_parse_action(remove_quotes)
    macro = "LEN_AND_STR(" + name + ")"
    number = pyparsing_common.number
    item = "{" + Suppress(constant) + "," + number.suppress() + "," + macro + "}"
    sentinel = Suppress("{" + delimited_list(Literal("0")) + "}")
    parser = (
        Suppress("partList[]") + "=" + "{" + delimited_list(item) + "," + sentinel + "}"
    )
    parser.ignore(c_style_comment)
    result = parser.search_string(filename.read_text(), max_matches=1)
    if not result:
        return []
    return [s.lstrip("%") for s in result[0]]


def extract_tags(filename: Path, with_args: bool = False) -> List[str]:
    """
    Extracts tag names from a constant array looking like this:

    static struct PreambleRec_s const preambleList[] = {
        {RPMTAG_NAME,		0, 0, 1, 0, LEN_AND_STR("name")},
        {RPMTAG_VERSION,		0, 0, 1, 0, LEN_AND_STR("version")},
        ...
        {0, 0, 0, 0}
    };

    Args:
        filename: Path to the file to extract tags from.
        with_args: Include only tags that accept arguments.

    Returns:
        List of tag names.
    """
    constant = Word(srange("[A-Z_]")).suppress()
    name = dbl_quoted_string("name").set_parse_action(remove_quotes)
    macro = "LEN_AND_STR(" + name + ")"
    number = pyparsing_common.number
    item = Group(
        "{"
        + constant
        + ","
        + number("type")
        + ","
        + number.suppress()
        + ","
        + number.suppress()
        + ","
        + number.suppress()
        + ","
        + macro
        + "}"
    )
    sentinel = Suppress("{" + delimited_list(Literal("0")) + "}")
    parser = (
        Suppress("preambleList[]")
        + "="
        + "{"
        + delimited_list(item)
        + ","
        + sentinel
        + "}"
    )
    parser.ignore(c_style_comment)
    result = parser.search_string(filename.read_text(), max_matches=1)
    if not result:
        return []
    return [t.name for t in result[0] if not with_args or t.type > 0]


def extract_arches(filename: Path) -> List[str]:
    """
    Extracts arch names from a list looking like this:

    arch_canon: athlon: athlon  1
    arch_canon: geode:  geode   1
    ...
    arch_canon: IP: sgi 7
    ...
    arch_canon: atariclone: m68kmint    13
    ...

    Args:
        filename: Path to the file to extract arches from.

    Returns:
        List of arch names.
    """
    identifier = pyparsing_common.identifier
    number = pyparsing_common.number
    parser = (
        Suppress("arch_canon:")
        + Combine(identifier + ":")
        + identifier.suppress()
        + number.suppress()
    )
    result = parser.search_string(filename.read_text())
    return [a[0] for a in result]


@click.group()
def extract():
    pass


@extract.command(
    help="Extract section names from the specified source file (typically build/parseSpec.c)."
)
@click.argument(
    "filename",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
def sections(filename: Path) -> None:
    for section in extract_sections(filename):
        click.echo(section)


@extract.command(
    help="Extract tag names from the specified source file (typically build/parsePreamble.c)."
)
@click.argument(
    "filename",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--with-args",
    is_flag=True,
    default=False,
    help="List only tags that accept arguments.",
)
def tags(filename: Path, with_args: bool = False) -> None:
    for tag in extract_tags(filename, with_args):
        click.echo(tag)


@extract.command(
    help="Extract arch names from the specified template file (typically rpmrc.in)."
)
@click.argument(
    "filename",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
def arches(filename: Path) -> None:
    for arch in extract_arches(filename):
        click.echo(arch)


if __name__ == "__main__":
    extract()
