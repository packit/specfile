# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from specfile.exceptions import SpecfileException
from specfile.sourcelist import Sourcelist, SourcelistEntry
from specfile.sources import ListSource, Patches, Sources, TagSource
from specfile.tags import Comments, Tag, Tags


@pytest.mark.parametrize(
    "tag_name, index",
    [
        ("Source", None),
        ("Source0", "0"),
        ("Patch0001", "0001"),
        ("Patch28", "28"),
        ("Patch99999", "99999"),
    ],
)
def test_tag_source_get_index(tag_name, index):
    ts = TagSource(Tag(tag_name, "", "", "", Comments()))
    assert ts._get_index() == index


@pytest.mark.parametrize(
    "ref_name, ref_separator, index, name, separator",
    [
        ("Source", ": ", 28, "Source28", ":"),
        ("Source0001", ":      ", 2, "Source0002", ":      "),
    ],
)
def test_sources_get_tag_format(ref_name, ref_separator, index, name, separator):
    sources = Sources(None, [])
    reference = TagSource(Tag(ref_name, "", "", ref_separator, Comments()))
    assert sources._get_tag_format(reference, index) == (name, separator)


@pytest.mark.parametrize(
    "tags, index",
    [
        (["Name", "Version"], 2),
        ([], 0),
    ],
)
def test_sources_get_initial_tag_setup(tags, index):
    sources = Sources(
        Tags([Tag(t, "test", "test", ": ", Comments()) for t in tags]), []
    )
    assert sources._get_initial_tag_setup() == (index, "Source0", ": ")


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
    assert [t.name for t in sources.tags] == deduplicated_tags


@pytest.mark.parametrize(
    "tags, sourcelists, index, location, source_index, cls",
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
def test_sources_insert(tags, sourcelists, index, location, source_index, cls):
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
        assert sources[index].index == source_index
        assert sources[index].location == location


@pytest.mark.parametrize(
    "ref_name, ref_separator, index, name, separator",
    [
        ("Patch99", ":      ", 100, "Patch100", ":     "),
        ("Patch9999", ":  ", 28, "Patch0028", ":  "),
        ("Source2", ":     ", 0, "Patch0", ":      "),
    ],
)
def test_patches_get_tag_format(ref_name, ref_separator, index, name, separator):
    patches = Patches(None, [])
    reference = TagSource(Tag(ref_name, "", "", ref_separator, Comments()))
    assert patches._get_tag_format(reference, index) == (name, separator)


@pytest.mark.parametrize(
    "tags, index",
    [
        (["Name", "Version", "Source0"], 3),
        (["Name", "Version", "Source0", "BuildRequires"], 3),
        (["Name", "Version"], 2),
        ([], 0),
    ],
)
def test_patches_get_initial_tag_setup(tags, index):
    patches = Patches(
        Tags([Tag(t, "test", "test", ": ", Comments()) for t in tags]), []
    )
    flexmock(patches).should_receive("_get_tag_format").and_return("Patch0", ": ")
    assert patches._get_initial_tag_setup() == (index, "Patch0", ": ")
