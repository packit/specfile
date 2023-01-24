# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy

import pytest
from flexmock import flexmock

from specfile.exceptions import SpecfileException
from specfile.sourcelist import Sourcelist, SourcelistEntry
from specfile.sources import ListSource, Patches, Sources, TagSource
from specfile.tags import Comments, Tag, Tags


@pytest.mark.parametrize(
    "tag_name, number",
    [
        ("Source", None),
        ("Source0", "0"),
        ("Patch0001", "0001"),
        ("Patch28", "28"),
        ("Patch99999", "99999"),
    ],
)
def test_tag_source_extract_number(tag_name, number):
    ts = TagSource(Tag(tag_name, "", "", Comments()))
    assert ts._extract_number() == number


@pytest.mark.parametrize(
    "tags, default, result",
    [
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
                ("Source2", "source2"),
            ],
            True,
            False,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source", "source0"),
                ("Source", "source1"),
                ("Source", "source2"),
            ],
            False,
            True,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source", "source0"),
            ],
            False,
            False,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source", "source0"),
            ],
            True,
            True,
        ),
    ],
)
def test_sources_detect_implicit_numbering(tags, default, result):
    sources = Sources(
        Tags([Tag(t, v, ": ", Comments()) for t, v in tags]),
        [],
        default_to_implicit_numbering=default,
    )
    assert sources._detect_implicit_numbering() == result


@pytest.mark.parametrize(
    "ref_name, ref_separator, number, name, separator",
    [
        ("Source", ": ", 28, "Source", ": "),
        ("Source0", ": ", 28, "Source28", ":"),
        ("Source0001", ":      ", 2, "Source0002", ":      "),
    ],
)
def test_sources_get_tag_format(ref_name, ref_separator, number, name, separator):
    sources = Sources(Tags(), [])
    reference = TagSource(Tag(ref_name, "", ref_separator, Comments()))
    assert sources._get_tag_format(reference, number) == (name, separator)


@pytest.mark.parametrize(
    "tags, number, index",
    [
        (["Name", "Version"], 0, 2),
        ([], 999, 0),
    ],
)
def test_sources_get_initial_tag_setup(tags, number, index):
    sources = Sources(Tags([Tag(t, "test", ": ", Comments()) for t in tags]), [])
    assert sources._get_initial_tag_setup(number) == (index, f"Source{number}", ": ")


@pytest.mark.parametrize(
    "tags, deduplicated_tags",
    [
        (["Source", "Source"], ["Source", "Source"]),
        (["Source0", "Source"], ["Source0", "Source"]),
        (
            ["Source0", "Source0", "Source", "Source"],
            ["Source0", "Source1", "Source", "Source"],
        ),
        (
            ["Source100", "Source100", "Source", "Source1028", "Source1011"],
            ["Source100", "Source101", "Source", "Source1028", "Source1011"],
        ),
        (
            ["Source2", "Source2", "Source4", "Source", "Source999"],
            ["Source2", "Source3", "Source4", "Source", "Source999"],
        ),
        (
            ["Source3", "Source4", "Source", "Source5"],
            ["Source3", "Source4", "Source", "Source6"],
        ),
        (
            [
                "Source",
                "Source",
                "Source100",
                "Source101",
                "Source101",
                "Source102",
                "Source",
            ],
            [
                "Source",
                "Source",
                "Source100",
                "Source101",
                "Source102",
                "Source103",
                "Source",
            ],
        ),
    ],
)
def test_sources_deduplicate_tag_names(tags, deduplicated_tags):
    sources = Sources(Tags([Tag(t, "test", ": ", Comments()) for t in tags]), [])
    sources._deduplicate_tag_names()
    assert [t.name for t in sources._tags] == deduplicated_tags


@pytest.mark.parametrize(
    "tags, sourcelists, index, location, number, cls",
    [
        ([("Name", "test"), ("Version", "0.1")], [], 0, "test", 0, TagSource),
        ([("Name", "test"), ("Version", "0.1")], [[]], 0, "test", 0, ListSource),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
            ],
            [],
            10,
            "test",
            2,
            TagSource,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
            ],
            [["source2", "source3"]],
            10,
            "test",
            4,
            ListSource,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
            ],
            [["source2", "source3"]],
            1,
            "test",
            1,
            TagSource,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source10", "source10"),
            ],
            [["source11", "source12"]],
            1,
            "test",
            10,
            TagSource,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
            ],
            [["source2", "source3"]],
            2,
            "test",
            2,
            ListSource,
        ),
        (
            [("Name", "test"), ("Version", "0.1"), ("Source0", "source0")],
            [],
            10,
            "source0",
            None,
            None,
        ),
    ],
)
def test_sources_insert(tags, sourcelists, index, location, number, cls):
    sources = Sources(
        Tags([Tag(t, v, ": ", Comments()) for t, v in tags]),
        [
            Sourcelist([SourcelistEntry(s, Comments()) for s in sl])
            for sl in sourcelists
        ],
    )
    if location in [v for t, v in tags if t.startswith(Sources.prefix)] + [
        s for sl in sourcelists for s in sl
    ]:
        with pytest.raises(SpecfileException):
            sources.insert(index, location)
    else:
        sources.insert(index, location)
        if index >= len(sources):
            index = len(sources) - 1
        assert isinstance(sources[index], cls)
        assert sources[index].number == number
        assert sources[index].location == location


@pytest.mark.parametrize(
    "tags, number, location, index",
    [
        ([("Name", "test"), ("Version", "0.1")], 28, "test", 0),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
                ("Source28", "source28"),
                ("Source999", "source999"),
            ],
            0,
            "test",
            0,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
                ("Source28", "source28"),
                ("Source999", "source999"),
            ],
            2,
            "test",
            2,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
                ("Source28", "source28"),
                ("Source999", "source999"),
            ],
            42,
            "test",
            3,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
                ("Source28", "source28"),
                ("Source999", "source999"),
            ],
            1000,
            "test",
            4,
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source28", "source28"),
                ("Source42", "source42"),
                ("Source5", "source5"),
                ("Source", "source"),
            ],
            37,
            "test",
            1,
        ),
    ],
)
def test_sources_insert_numbered(tags, number, location, index):
    sources = Sources(Tags([Tag(t, v, ": ", Comments()) for t, v in tags]), [])
    if location in [v for t, v in tags if t.startswith(Sources.prefix)]:
        with pytest.raises(SpecfileException):
            sources.insert_numbered(number, location)
    else:
        assert sources.insert_numbered(number, location) == index
        assert isinstance(sources[index], TagSource)
        assert sources[index].number == number
        assert sources[index].location == location


@pytest.mark.parametrize(
    "tags, sourcelists, number, new_tags, new_sourcelists",
    [
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
            ],
            [],
            1,
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
            ],
            [],
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
            ],
            [],
            2,
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
            ],
            [],
        ),
        (
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
            ],
            [["source2", "source3"]],
            2,
            [
                ("Name", "test"),
                ("Version", "0.1"),
                ("Source0", "source0"),
                ("Source1", "source1"),
            ],
            [["source3"]],
        ),
    ],
)
def test_sources_remove_numbered(tags, sourcelists, number, new_tags, new_sourcelists):
    tags = Tags([Tag(t, v, ": ", Comments()) for t, v in tags])
    sourcelists = [
        Sourcelist([SourcelistEntry(s, Comments()) for s in sl]) for sl in sourcelists
    ]
    sources = Sources(tags, sourcelists)
    sources.remove_numbered(number)
    assert tags == Tags([Tag(t, v, ": ", Comments()) for t, v in new_tags])
    assert sourcelists == [
        Sourcelist([SourcelistEntry(s, Comments()) for s in sl])
        for sl in new_sourcelists
    ]


@pytest.mark.parametrize(
    "ref_name, ref_separator, number, name, separator",
    [
        ("Patch99", ":      ", 100, "Patch100", ":     "),
        ("Patch9999", ":  ", 28, "Patch28", ":    "),
        ("Patch0999", ":  ", 28, "Patch0028", ":  "),
        ("Source2", ":     ", 0, "Patch0", ":      "),
    ],
)
def test_patches_get_tag_format(ref_name, ref_separator, number, name, separator):
    patches = Patches(Tags(), [])
    reference = TagSource(Tag(ref_name, "", ref_separator, Comments()))
    assert patches._get_tag_format(reference, number) == (name, separator)


@pytest.mark.parametrize(
    "tags, number, index",
    [
        (["Name", "Version", "Source0"], 0, 3),
        (["Name", "Version", "Source0", "BuildRequires"], 1, 3),
        (["Name", "Version"], 2, 2),
        ([], 999, 0),
    ],
)
def test_patches_get_initial_tag_setup(tags, number, index):
    patches = Patches(Tags([Tag(t, "test", ": ", Comments()) for t in tags]), [])
    flexmock(patches).should_receive("_get_tag_format").and_return(
        f"Patch{number}", ": "
    )
    assert patches._get_initial_tag_setup(number) == (index, f"Patch{number}", ": ")


def test_copy_sources():
    sources = Sources(
        Tags([Tag("Name", "test", ": ", Comments())]),
        [
            Sourcelist([SourcelistEntry("%{name}-%{version}.tar.gz", Comments())]),
        ],
    )
    shallow_copy = copy.copy(sources)
    assert shallow_copy == sources
    assert shallow_copy is not sources
    assert shallow_copy._tags is sources._tags
    assert shallow_copy._sourcelists is sources._sourcelists
    deep_copy = copy.deepcopy(sources)
    assert deep_copy == sources
    assert deep_copy is not sources
    assert deep_copy._tags is not sources._tags
    assert deep_copy._sourcelists is not sources._sourcelists
