# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from specfile.sections import Section
from specfile.sourcelist import Sourcelist, SourcelistEntry
from specfile.tags import Comment, Comments


def test_parse():
    sourcelist = Sourcelist.parse(
        Section(
            "sourcelist",
            [
                "https://example.com/example-0.1.0.tar.xz",
                "",
                "# test suite",
                "tests.tar.xz",
                "",
                "",
            ],
        )
    )
    assert len(sourcelist) == 2
    assert sourcelist[0].location == "https://example.com/example-0.1.0.tar.xz"
    assert not sourcelist[0].comments
    assert sourcelist[1].location == "tests.tar.xz"
    assert sourcelist[1].comments[0].text == "test suite"


def test_get_raw_section_data():
    sourcelist = Sourcelist(
        [
            SourcelistEntry("https://example.com/example-0.1.0.tar.xz", Comments()),
            SourcelistEntry("tests.tar.xz", Comments([Comment("test suite")], [""])),
        ],
        ["", ""],
    )
    assert sourcelist.get_raw_section_data() == [
        "https://example.com/example-0.1.0.tar.xz",
        "",
        "# test suite",
        "tests.tar.xz",
        "",
        "",
    ]
