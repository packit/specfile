# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

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
    ts = TagSource(Tag(tag_name, "", "", "", Comments()))
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
        Tags([Tag(t, v, v, ": ", Comments()) for t, v in tags]),
        [],
        default_to_implicit_numbering=default,
    )
    assert sources._detect_implicit_numbering() == result


@pytest.mark.parametrize(
    "ref_name, ref_separator, number, name, separator",
    [
        ("Source", ": ", 28, "Source28", ":"),
        ("Source0001", ":      ", 2, "Source0002", ":      "),
    ],
)
def test_sources_get_tag_format(ref_name, ref_separator, number, name, separator):
    sources = Sources(Tags(), [])
    reference = TagSource(Tag(ref_name, "", "", ref_separator, Comments()))
    assert sources._get_tag_format(reference, number) == (name, separator)


@pytest.mark.parametrize(
    "tags, number, index",
    [
        (["Name", "Version"], 0, 2),
        ([], 999, 0),
    ],
)
def test_sources_get_initial_tag_setup(tags, number, index):
    sources = Sources(
        Tags([Tag(t, "test", "test", ": ", Comments()) for t in tags]), []
    )
    assert sources._get_initial_tag_setup(number) == (index, f"Source{number}", ": ")


@pytest.mark.parametrize(
    "tags, deduplicated_tags",
    [
        (["Source", "Source0"], ["Source", "Source1"]),
        (["Source0028", "Source28"], ["Source0028", "Source0029"]),
        (
            ["Source2", "Source2", "Source3", "Source3"],
            ["Source2", "Source3", "Source4", "Source5"],
        ),
    ],
)
def test_sources_deduplicate_tag_names(tags, deduplicated_tags):
    sources = Sources(
        Tags([Tag(t, "test", "test", ": ", Comments()) for t in tags]), []
    )
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
        Tags([Tag(t, v, v, ": ", Comments()) for t, v in tags]),
        [
            Sourcelist([SourcelistEntry(s, Comments()) for s in sl])
            for sl in sourcelists
        ],
    )
    if location in [v for t, v in tags if t.startswith(Sources.PREFIX)] + [
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
    sources = Sources(Tags([Tag(t, v, v, ": ", Comments()) for t, v in tags]), [])
    if location in [v for t, v in tags if t.startswith(Sources.PREFIX)]:
        with pytest.raises(SpecfileException):
            sources.insert_numbered(number, location)
    else:
        assert sources.insert_numbered(number, location) == index
        assert isinstance(sources[index], TagSource)
        assert sources[index].number == number
        assert sources[index].location == location


@pytest.mark.parametrize(
    "ref_name, ref_separator, number, name, separator",
    [
        ("Patch99", ":      ", 100, "Patch100", ":     "),
        ("Patch9999", ":  ", 28, "Patch0028", ":  "),
        ("Source2", ":     ", 0, "Patch0", ":      "),
    ],
)
def test_patches_get_tag_format(ref_name, ref_separator, number, name, separator):
    patches = Patches(Tags(), [])
    reference = TagSource(Tag(ref_name, "", "", ref_separator, Comments()))
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
    patches = Patches(
        Tags([Tag(t, "test", "test", ": ", Comments()) for t in tags]), []
    )
    flexmock(patches).should_receive("_get_tag_format").and_return(
        f"Patch{number}", ": "
    )
    assert patches._get_initial_tag_setup(number) == (index, f"Patch{number}", ": ")
