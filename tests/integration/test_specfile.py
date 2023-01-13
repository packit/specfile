# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
import datetime
import subprocess

import pytest
import rpm
from flexmock import flexmock

from specfile.exceptions import RPMException, SpecfileException
from specfile.prep import AutopatchMacro, AutosetupMacro, PatchMacro, SetupMacro
from specfile.sections import Section
from specfile.specfile import Specfile


def test_parse(spec_multiple_sources):
    spec = Specfile(spec_multiple_sources)
    prep = spec.rpm_spec.prep
    # remove all sources
    for path in spec.sourcedir.iterdir():
        if not path.samefile(spec.path):
            path.unlink()
    spec = Specfile(spec_multiple_sources)
    assert spec.rpm_spec.prep == prep


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
    "rpmdev_packager_available, entry, author, email, timestamp, evr, result",
    [
        (False, None, None, None, None, None, None),
        (
            True,
            "test",
            None,
            None,
            datetime.date(2022, 2, 1),
            None,
            Section(
                "changelog",
                data=["* Tue Feb 01 2022 John Doe <john@doe.net> - 0.1-1", "test"],
            ),
        ),
        (
            True,
            "test",
            None,
            None,
            datetime.date(2022, 2, 1),
            "%{version}-%{release}",
            Section(
                "changelog",
                data=["* Tue Feb 01 2022 John Doe <john@doe.net> - 0.1-1", "test"],
            ),
        ),
        (
            True,
            "test",
            None,
            None,
            datetime.date(2022, 2, 1),
            "0.1-1",
            Section(
                "changelog",
                data=["* Tue Feb 01 2022 John Doe <john@doe.net> - 0.1-1", "test"],
            ),
        ),
        (
            True,
            "test",
            None,
            None,
            datetime.date(2022, 2, 1),
            "0.2-1.1",
            Section(
                "changelog",
                data=["* Tue Feb 01 2022 John Doe <john@doe.net> - 0.2-1.1", "test"],
            ),
        ),
        (
            True,
            "test",
            "Bill Packager",
            None,
            datetime.date(2022, 2, 1),
            None,
            Section(
                "changelog", data=["* Tue Feb 01 2022 Bill Packager - 0.1-1", "test"]
            ),
        ),
        (
            True,
            "test",
            "Bill Packager",
            "bill@packager.net",
            datetime.date(2022, 2, 1),
            None,
            Section(
                "changelog",
                data=[
                    "* Tue Feb 01 2022 Bill Packager <bill@packager.net> - 0.1-1",
                    "test",
                ],
            ),
        ),
        (
            True,
            "test",
            "Bill Packager",
            "bill@packager.net",
            datetime.datetime(2022, 2, 1, 9, 28, 13),
            None,
            Section(
                "changelog",
                data=[
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
            None,
            Section(
                "changelog",
                data=[
                    "* Tue Feb 01 09:28:13 UTC 2022 Bill Packager <bill@packager.net> - 0.1-1",
                    "line 1",
                    "line 2",
                ],
            ),
        ),
    ],
)
def test_add_changelog_entry(
    spec_minimal,
    rpmdev_packager_available,
    entry,
    author,
    email,
    timestamp,
    evr,
    result,
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
            spec.add_changelog_entry(entry, author, email, timestamp, evr)
    else:
        spec.add_changelog_entry(entry, author, email, timestamp, evr)
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
    assert spec.rpm_spec.sourceHeader[rpm.RPMTAG_VERSION] == spec.expanded_version
    assert spec.rpm_spec.sourceHeader[rpm.RPMTAG_RELEASE] == spec.expanded_raw_release
    spec.raw_release = release
    with spec.tags() as tags:
        assert tags.release.value == release
    assert spec.rpm_spec.sourceHeader[rpm.RPMTAG_RELEASE] == spec.expanded_raw_release


@pytest.mark.parametrize(
    "location, number, comment",
    [
        ("patchX.patch", None, None),
        ("patchX.patch", 0, None),
        ("patch2.patch", None, None),
        ("patch3.patch", 3, "patch3"),
    ],
)
def test_add_patch(spec_autosetup, location, number, comment):
    spec = Specfile(spec_autosetup)
    if number == 0 or location == "patch2.patch":
        with pytest.raises(SpecfileException):
            spec.add_patch(location, number, comment)
    else:
        spec.add_patch(location, number, comment)
        with spec.patches() as patches:
            assert patches[-1].location == location
            if number is not None:
                assert patches[-1].number == number
            else:
                assert patches[-1].number == 3
        with spec.sections() as sections:
            if comment is not None:
                assert sections.package[-4] == f"# {comment}"


def test_remove_patches(spec_commented_patches):
    spec = Specfile(spec_commented_patches)
    with spec.patches() as patches:
        del patches[1:3]
        patches.remove_numbered(5)
    with spec.sections() as sections:
        assert sections.package[-11:-2] == [
            "# this is a downstream-only patch",
            "Patch0:         patch0.patch",
            "",
            "# these two patches are related to each other",
            "Patch3:         patch3.patch",
            "Patch4:         patch4.patch",
            "",
            "# this is patch6",
            "Patch6:         patch6.patch",
        ]


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


def test_update_tag(spec_macros):
    spec = Specfile(spec_macros)
    spec.update_tag("Version", "1.2.3~beta4")
    with spec.macro_definitions() as md:
        assert md.majorver.body == "1"
        assert md.minorver.body == "2"
        assert md.patchver.body == "3"
        assert md.prever.body == "beta4"
        assert md.package_version.body == "%{majorver}.%{minorver}.%{patchver}"
    assert spec.version == "%{package_version}%{?prever:~%{prever}}"
    spec.update_tag("Version", "4.0~alpha1")
    with spec.macro_definitions() as md:
        assert md.majorver.body == "1"
        assert md.minorver.body == "2"
        assert md.patchver.body == "3"
        assert md.prever.body == "alpha1"
        assert md.package_version.body == "4.0"
    assert spec.version == "%{package_version}%{?prever:~%{prever}}"
    spec.update_tag("Version", "5.3.3")
    with spec.macro_definitions() as md:
        assert md.majorver.body == "1"
        assert md.minorver.body == "2"
        assert md.patchver.body == "3"
        assert md.prever.body == "alpha1"
        assert md.package_version.body == "4.0"
    assert spec.version == "5.3.3"
    spec.update_tag("Release", "2%{?dist}")
    assert spec.raw_release == "%{release}"
    with spec.macro_definitions() as md:
        assert md.release.body == "2%{?dist}"
    spec.update_tag(
        "Source0",
        "https://example.com/archived_releases/test/v6.0.0/test-v6.0.0.tar.xz",
    )
    assert spec.version == "6.0.0"
    with spec.sources() as sources:
        assert (
            sources[0].location
            == "https://example.com/archived_releases/%{name}/v%{version}/"
            "%{name}-v%{version}.tar.xz"
        )
    spec.update_tag(
        "Source0", "https://example.com/archived_releases/test-v7.2.1.tar.xz"
    )
    assert spec.version == "6.0.0"
    with spec.sources() as sources:
        assert (
            sources[0].location
            == "https://example.com/archived_releases/test-v7.2.1.tar.xz"
        )
    spec.update_tag("Source1", "tests-86.tar.xz")
    with spec.macro_definitions() as md:
        assert md.majorver.body == "1"
        assert md.minorver.body == "2"
    with spec.sources() as sources:
        assert sources[1].location == "tests-86.tar.xz"


def test_multiple_instances(spec_minimal, spec_autosetup):
    spec1 = Specfile(spec_minimal)
    spec2 = Specfile(spec_autosetup)
    spec1.version = "14.2"
    assert spec2.expanded_version == "0.1"
    with spec2.sources() as sources:
        assert sources[0].expanded_location == "test-0.1.tar.xz"
        sources.append("tests-%{version}.tar.xz")
        assert sources[1].expanded_location == "tests-0.1.tar.xz"


def test_includes(spec_includes):
    spec = Specfile(spec_includes)
    assert not spec.tainted
    with spec.patches() as patches:
        assert not patches
    assert spec.expand("%patches")
    with spec.tags() as tags:
        assert tags.provides.value.startswith("%(")
        for i in range(1, 4):
            assert f"test{i}-0.1" in tags.provides.expanded_value
    with spec.sections() as sections:
        assert sections.description[0] == "%include %{SOURCE3}"
        assert sections.description[1] == "%(cat %{S:4})"
    assert spec.parsed_sections.description[0] == "Test package"
    assert spec.parsed_sections.description[1] == "Additional description"
    for inc in ["patches.inc", "provides.inc", "description1.inc", "description2.inc"]:
        (spec.sourcedir / inc).unlink()
    with pytest.raises(RPMException):
        spec = Specfile(spec_includes)
    spec = Specfile(spec_includes, force_parse=True)
    assert spec.tainted
    with spec.patches() as patches:
        assert not patches
    assert not spec.expand("%patches")
    with spec.tags() as tags:
        assert tags.provides.value.startswith("%(")
        assert tags.provides.expanded_value == "DUMMY-0.1"
    with spec.sections() as sections:
        assert sections.description[0] == "%include %{SOURCE3}"
        assert sections.description[1] == "%(cat %{S:4})"
    assert not "".join(spec.parsed_sections.description)
    for inc in ["macros1.inc", "macros2.inc"]:
        (spec.sourcedir / inc).unlink()
        with pytest.raises(RPMException):
            spec = Specfile(spec_includes, force_parse=True)
        assert not (spec.sourcedir / inc).is_file()


def test_shell_expansions(spec_shell_expansions):
    spec = Specfile(spec_shell_expansions)
    assert spec.expanded_version == "1035.4200"
    assert "C.UTF-8" in spec.expand("%numeric_locale")


def test_context_management(spec_autosetup, spec_traditional):
    spec = Specfile(spec_autosetup)
    with spec.tags() as tags:
        tags.license.value = "BSD"
        assert spec.license == "BSD"
        spec.license = "BSD-3-Clause"
        tags.patch0.value = "first_patch.patch"
        with spec.patches() as patches:
            assert patches[0].location == "first_patch.patch"
            patches[0].location = "patch_0.patch"
    assert spec.license == "BSD-3-Clause"
    with spec.patches() as patches:
        assert patches[0].location == "patch_0.patch"
    spec1 = Specfile(spec_autosetup)
    spec2 = Specfile(spec_traditional)
    with spec1.sections() as sections1, spec2.sections() as sections2:
        assert sections1 is not sections2
    with spec1.tags() as tags1, spec2.tags() as tags2:
        assert tags1 is not tags2
        assert tags1 == tags2


def test_copy(spec_autosetup):
    spec = Specfile(spec_autosetup)
    shallow_copy = copy.copy(spec)
    assert shallow_copy == spec
    assert shallow_copy is not spec
    assert shallow_copy._lines is spec._lines
    assert shallow_copy._parser is spec._parser
    deep_copy = copy.deepcopy(spec)
    assert deep_copy == spec
    assert deep_copy is not spec
    assert deep_copy._lines is not spec._lines
    assert deep_copy._parser is not spec._parser
