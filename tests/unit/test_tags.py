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
            [
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
            ],
        ),
        Section(
            "package",
            [
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
        ],
        ["%endif"],
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
    ]


def test_copy_tags():
    tags = Tags(
        [
            Tag("Name", "test", "test", ": ", Comments()),
        ]
    )
    tags_copy = copy.deepcopy(tags)
    assert tags == tags_copy
