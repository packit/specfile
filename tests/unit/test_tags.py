# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy

import pytest

from specfile.sections import Section
from specfile.tags import Comment, Comments, Tag, Tags


def test_find():
    tags = Tags(
        [
            Tag("Name", "test", "test", ": ", Comments()),
            Tag("Version", "0.1", "0.1", ": ", Comments()),
            Tag("Release", "1%{?dist}", "1.fc35", ": ", Comments()),
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
                "Requires:          make",
                "Requires(post):    bash",
                "",
                "%{?fedora:Suggests:          diffutils}",
            ],
        ),
        Section(
            "package",
            data=[
                "",
                "",
                "",
                "# this is a test package",
                "# not to be used in production",
                "Name:    test",
                "Version: 1.0",
                "  # this is a valid comment",
                "Release: 1.fc35",
                "",
                "",
                "",
                "",
                "",
                "Requires:          make",
                "Requires(post):    bash",
                "",
                "Suggests:          diffutils",
            ],
        ),
    )
    assert tags[0].name == "Name"
    assert tags[0].comments[0].text == "this is a test package"
    assert tags[0].comments[1].text == "not to be used in production"
    assert tags[1].name == "Version"
    assert tags[1].value == "%{ver_major}.%{ver_minor}"
    assert tags[1].valid
    assert tags[1].expanded_value == "1.0"
    assert not tags[1].comments
    assert tags.release.comments[0].prefix == "  # "
    assert tags.epoch.name == "Epoch"
    assert not tags.epoch.valid
    assert tags.requires.value == "make"
    assert "requires(post)" in tags
    assert tags[-2].name == "Requires(post)"
    assert tags[-1].name == "Suggests"
    assert tags.suggests.value == "diffutils"


def test_get_raw_section_data():
    tags = Tags(
        [
            Tag(
                "Name",
                "test",
                "test",
                ":    ",
                Comments(
                    [
                        Comment("this is a test package"),
                        Comment("not to be used in production"),
                    ],
                    ["%global ver_major 1", "%global ver_minor 0", ""],
                ),
            ),
            Tag("Version", "%{ver_major}.%{ver_minor}", "1.0", ": ", Comments()),
            Tag(
                "Release",
                "1%{?dist}",
                "1.fc35",
                ": ",
                Comments([Comment("this is a valid comment", "  # ")]),
            ),
            Tag("Epoch", "1", "", ":   ", Comments([], ["", "%if 0"])),
            Tag(
                "Requires", "make", "make", ":          ", Comments([], ["%endif", ""])
            ),
            Tag("Requires(post)", "bash", "bash", ":    ", Comments()),
            Tag(
                "Suggests",
                "diffutils",
                "diffutils",
                ":          ",
                Comments([], [""]),
                "%{?fedora:",
                "}",
            ),
        ],
        [],
    )
    assert tags.get_raw_section_data() == [
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
        "Requires:          make",
        "Requires(post):    bash",
        "",
        "%{?fedora:Suggests:          diffutils}",
    ]


def test_copy_tags():
    tags = Tags(
        [
            Tag("Name", "test", "test", ": ", Comments()),
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
