# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy

import pytest

from specfile.sections import Section
from specfile.tags import Comment, Comments, Tag, Tags


def test_find():
    tags = Tags(
        [
            Tag("Name", "test", ": ", Comments()),
            Tag("Version", "0.1", ": ", Comments()),
            Tag("Release", "1%{?dist}", ": ", Comments()),
        ]
    )
    assert tags.find("version") == 1
    with pytest.raises(ValueError):
        tags.find("Epoch")


def test_parse():
    tags = Tags.parse(
        Section(
            "package",
            data=[
                "%{?scl:%scl_package scltest}",
                "",
                "%global ver_major 1",
                "%global ver_minor 0",
                "",
                "# this is a test package",
                "# not to be used in production",
                "Name:    test",
                "Version: %{ver_major}.%{ver_minor}",
                "  # this is a valid comment",
                "Release: 1%{?dist}",
                "",
                "%if 0",
                "Epoch:   1",
                "%endif",
                "",
                "License: %{shrink:",
                "             MIT AND",
                "             (MIT OR Apache-2.0)",
                "          }",
                "",
                "Requires:          make ",
                "Requires(post):    bash",
                "",
                "Provides:          testX = %{version}-%{release}",
                "Provides:          bundled(superlib) = 2.42.0",
                "",
                "%{?fedora:Suggests:          diffutils}",
            ],
        )
    )
    assert tags[0].comments._preceding_lines[0] == "%{?scl:%scl_package scltest}"
    assert tags[0].name == "Name"
    assert tags[0].comments[0].text == "this is a test package"
    assert tags[0].comments[1].text == "not to be used in production"
    assert tags[1].name == "Version"
    assert tags[1].value == "%{ver_major}.%{ver_minor}"
    assert not tags[1].comments
    assert tags.release.comments[0].prefix == "  # "
    assert tags.epoch.name == "Epoch"
    assert tags[-6].name == "License"
    assert (
        tags[-6].value == "%{shrink:\n"
        "             MIT AND\n"
        "             (MIT OR Apache-2.0)\n"
        "          }"
    )
    assert tags.requires.value == "make"
    assert "requires(post)" in tags
    assert tags[-4].name == "Requires(post)"
    assert tags[-3].name == "Provides"
    assert tags[-3].value == "testX = %{version}-%{release}"
    assert tags[-2].name == "Provides"
    assert tags[-2].value == "bundled(superlib) = 2.42.0"
    assert tags[-1].name == "Suggests"
    assert tags.suggests.value == "diffutils"


def test_get_raw_section_data():
    tags = Tags(
        [
            Tag(
                "Name",
                "test",
                ":    ",
                Comments(
                    [
                        Comment("this is a test package"),
                        Comment("not to be used in production"),
                    ],
                    [
                        "%{?scl:%scl_package scltest}",
                        "",
                        "%global ver_major 1",
                        "%global ver_minor 0",
                        "",
                    ],
                ),
            ),
            Tag("Version", "%{ver_major}.%{ver_minor}", ": ", Comments()),
            Tag(
                "Release",
                "1%{?dist}",
                ": ",
                Comments([Comment("this is a valid comment", "  # ")]),
            ),
            Tag("Epoch", "1", ":   ", Comments([], ["", "%if 0"])),
            Tag(
                "License",
                "%{shrink:\n"
                "             MIT AND\n"
                "             (MIT OR Apache-2.0)\n"
                "          }",
                ": ",
                Comments([], ["%endif", ""]),
            ),
            Tag(
                "Requires",
                "make",
                ":          ",
                Comments([], [""]),
                True,
                "",
                " ",
            ),
            Tag("Requires(post)", "bash", ":    ", Comments()),
            Tag(
                "Suggests",
                "diffutils",
                ":          ",
                Comments([], [""]),
                True,
                "%{?fedora:",
                "}",
            ),
        ],
        [],
    )
    assert tags.get_raw_section_data() == [
        "%{?scl:%scl_package scltest}",
        "",
        "%global ver_major 1",
        "%global ver_minor 0",
        "",
        "# this is a test package",
        "# not to be used in production",
        "Name:    test",
        "Version: %{ver_major}.%{ver_minor}",
        "  # this is a valid comment",
        "Release: 1%{?dist}",
        "",
        "%if 0",
        "Epoch:   1",
        "%endif",
        "",
        "License: %{shrink:",
        "             MIT AND",
        "             (MIT OR Apache-2.0)",
        "          }",
        "",
        "Requires:          make ",
        "Requires(post):    bash",
        "",
        "%{?fedora:Suggests:          diffutils}",
    ]


def test_copy_tags():
    tags = Tags(
        [
            Tag("Name", "test", ": ", Comments()),
        ]
    )
    shallow_copy = copy.copy(tags)
    assert shallow_copy == tags
    assert shallow_copy is not tags
    assert shallow_copy[0] is tags[0]
    deep_copy = copy.deepcopy(tags)
    assert deep_copy == tags
    assert deep_copy is not tags
    assert deep_copy[0] is not tags[0]
