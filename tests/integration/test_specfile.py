# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime
import subprocess

import pytest
from flexmock import flexmock

from specfile.exceptions import SpecfileException
from specfile.sections import Section
from specfile.specfile import Specfile


def test_parse(spec_multiple_sources):
    spec = Specfile(spec_multiple_sources)
    prep = spec._spec.prep
    # remove all sources
    for path in spec.sourcedir.iterdir():
        if not path.samefile(spec.path):
            path.unlink()
    spec = Specfile(spec_multiple_sources)
    assert spec._spec.prep == prep


def test_sources(spec_minimal):
    spec = Specfile(spec_minimal)
    source = "test.tar.gz"
    with spec.sources() as sources:
        assert not sources
        sources.append(source)
        assert sources.count(source) == len(sources) == 1
    with spec.tags() as tags:
        assert [source] == [t.value for t in tags if t.name.startswith("Source")]
    with spec.sources() as sources:
        sources.remove(source)
        assert not sources
        sources.insert(0, source)
        assert sources[0].location == source
        sources.clear()
        assert not sources


def test_patches(spec_patchlist):
    spec = Specfile(spec_patchlist)
    patch = "test.patch"
    with spec.patches() as patches:
        patches.insert(0, patch)
        assert patches[0].location == patch
        assert patches[1].index == 1
    with spec.tags() as tags:
        assert len([t for t in tags if t.name.startswith("Patch")]) == 2
    with spec.patches() as patches:
        patches.remove(patch)
        patches.insert(1, patch)
        patches[1].comments.append("test")
    with spec.sections() as sections:
        assert len([sl for sl in sections.patchlist if sl]) == 4
        assert sections.patchlist[0] == "# test"


@pytest.mark.parametrize(
    "rpmdev_packager_available, entry, author, email, timestamp, result",
    [
        (False, None, None, None, None, None),
        (
            True,
            "test",
            None,
            None,
            datetime.date(2022, 2, 1),
            Section(
                "changelog",
                ["* Tue Feb 01 2022 John Doe <john@doe.net> - 0.1-1", "test"],
            ),
        ),
        (
            True,
            "test",
            "Bill Packager",
            None,
            datetime.date(2022, 2, 1),
            Section("changelog", ["* Tue Feb 01 2022 Bill Packager - 0.1-1", "test"]),
        ),
        (
            True,
            "test",
            "Bill Packager",
            "bill@packager.net",
            datetime.date(2022, 2, 1),
            Section(
                "changelog",
                ["* Tue Feb 01 2022 Bill Packager <bill@packager.net> - 0.1-1", "test"],
            ),
        ),
        (
            True,
            "test",
            "Bill Packager",
            "bill@packager.net",
            datetime.datetime(2022, 2, 1, 9, 28, 13),
            Section(
                "changelog",
                [
                    "* Tue Feb 01 09:28:13 UTC 2022 Bill Packager <bill@packager.net> - 0.1-1",
                    "test",
                ],
            ),
        ),
        (
            True,
            ["line 1", "line 2"],
            "Bill Packager",
            "bill@packager.net",
            datetime.datetime(2022, 2, 1, 9, 28, 13),
            Section(
                "changelog",
                [
                    "* Tue Feb 01 09:28:13 UTC 2022 Bill Packager <bill@packager.net> - 0.1-1",
                    "line 1",
                    "line 2",
                ],
            ),
        ),
    ],
)
def test_add_changelog_entry(
    spec_minimal, rpmdev_packager_available, entry, author, email, timestamp, result
):
    if not rpmdev_packager_available:
        flexmock(subprocess).should_receive("check_output").with_args(
            "rpmdev-packager"
        ).and_raise(FileNotFoundError)
    elif author is None:
        flexmock(subprocess).should_receive("check_output").with_args(
            "rpmdev-packager"
        ).and_return(b"John Doe <john@doe.net>")
    spec = Specfile(spec_minimal)
    if not rpmdev_packager_available:
        with pytest.raises(SpecfileException):
            spec.add_changelog_entry(entry, author, email, timestamp)
    else:
        spec.add_changelog_entry(entry, author, email, timestamp)
        with spec.sections() as sections:
            assert sections.changelog[: len(result)] == result
