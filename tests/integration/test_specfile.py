# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime
import subprocess

import pytest
import rpm
from flexmock import flexmock

from specfile.exceptions import SpecfileException
from specfile.prep import AutopatchMacro, AutosetupMacro, PatchMacro, SetupMacro
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


def test_prep_traditional(spec_traditional):
    spec = Specfile(spec_traditional)
    with spec.prep() as prep:
        assert AutosetupMacro not in prep.macros
        assert AutopatchMacro not in prep.macros
        assert isinstance(prep.macros[0], SetupMacro)
        assert prep.macros[0] == prep.setup
        for i, m in enumerate(prep.macros[1:]):
            assert isinstance(m, PatchMacro)
            assert m.number == i
            assert m.options.p == 1
        prep.remove_patch_macro(0)
        assert len([m for m in prep.macros if isinstance(m, PatchMacro)]) == 2
        prep.add_patch_macro(0, p=2, b=".test")
        assert len(prep.macros) == 4
        assert prep.patch0.options.p == 2
        assert prep.patch0.options.b == ".test"
        prep.patch0.options.b = ".test2"
        prep.patch0.options.E = True
    with spec.sections() as sections:
        assert sections.prep[1] == "%patch0 -p2 -b .test2 -E"


def test_prep_autosetup(spec_autosetup):
    spec = Specfile(spec_autosetup)
    with spec.prep() as prep:
        assert len(prep.macros) == 1
        assert AutosetupMacro in prep.macros
        assert SetupMacro not in prep.macros
        assert PatchMacro not in prep.macros
        assert prep.autosetup.options.p == 1


def test_prep_autopatch(spec_autopatch):
    spec = Specfile(spec_autopatch)
    with spec.prep() as prep:
        assert len(prep.macros) == 4
        assert prep.macros[1].options.M == 2
        assert prep.macros[2].options.positional == [3]
        assert prep.macros[3].options.m == 4
        del prep.macros[1]
        del prep.macros[2]
        prep.autopatch.options.positional = list(range(7))
    with spec.sections() as sections:
        assert sections.prep[0] == "%autosetup -N"
        assert sections.prep[3] == "%autopatch -p1 0 1 2 3 4 5 6"


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
        assert patches[1].number == 1
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


@pytest.mark.parametrize(
    "version, release",
    [
        ("0.2", "3"),
        ("67", "1"),
        ("1.4.6", "0.1rc5"),
    ],
)
def test_set_version_and_release(spec_minimal, version, release):
    spec = Specfile(spec_minimal)
    spec.set_version_and_release(version, release)
    assert spec.version == version
    assert spec.release == release
    assert spec.raw_release.startswith(release)
    with spec.tags() as tags:
        assert tags.version.value == spec.version
        assert tags.release.value == spec.raw_release
    assert spec._spec.sourceHeader[rpm.RPMTAG_VERSION] == spec.expanded_version
    assert spec._spec.sourceHeader[rpm.RPMTAG_RELEASE] == spec.expanded_raw_release
    spec.raw_release = release
    with spec.tags() as tags:
        assert tags.release.value == release
    assert spec._spec.sourceHeader[rpm.RPMTAG_RELEASE] == spec.expanded_raw_release


@pytest.mark.skipif(
    rpm.__version__ < "4.16", reason="%autochangelog requires rpm 4.16 or higher"
)
def test_autochangelog(spec_rpmautospec):
    spec = Specfile(spec_rpmautospec)
    assert spec.has_autochangelog
    with spec.changelog() as changelog:
        assert len(changelog) == 0
    with spec.sections() as sections:
        changelog = sections.changelog.copy()
    spec.add_changelog_entry("test")
    with spec.sections() as sections:
        assert sections.changelog == changelog
