#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import re
import sys
from pathlib import Path

import click
from extract import extract_arches, extract_sections, extract_tags

SECTIONS_SOURCE = Path("build/parseSpec.cc")
TAGS_SOURCE = Path("build/parsePreamble.cc")
ARCHES_SOURCE = Path("rpmrc.in")


@click.command(
    help="Update CONSTANTS_FILE with constants extracted from RPM_SOURCE_TREE."
)
@click.argument(
    "constants_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    default=Path("specfile/constants.py"),
)
@click.argument(
    "rpm_source_tree",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
)
def update_constants(constants_file: Path, rpm_source_tree: Path) -> None:
    section_names = extract_sections(rpm_source_tree / SECTIONS_SOURCE)
    tag_names = extract_tags(rpm_source_tree / TAGS_SOURCE)
    tags_with_args = extract_tags(rpm_source_tree / TAGS_SOURCE, with_args=True)
    arch_names = extract_arches(rpm_source_tree / ARCHES_SOURCE)
    content = original_content = constants_file.read_text()
    for constant, values in (
        ("SECTION_NAMES", section_names),
        ("TAG_NAMES", tag_names),
        ("TAGS_WITH_ARGS", tags_with_args),
        ("ARCH_NAMES", arch_names),
    ):
        formatted_values = "\n".join([f'    "{v}",' for v in sorted(set(values))])
        content = re.sub(
            rf"({constant}\s*=\s*{{).*?(}})",
            rf"\g<1>\n{formatted_values}\n\g<2>",
            content,
            flags=re.DOTALL,
        )
    if content == original_content:
        sys.exit(100)
        return
    constants_file.write_text(content)


if __name__ == "__main__":
    update_constants()
