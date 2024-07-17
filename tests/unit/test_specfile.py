# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from specfile.specfile import Specfile


@pytest.mark.parametrize(
    "raw_release, release, dist, minorbump",
    [
        ("1%{?dist}", "1", "%{?dist}", None),
        ("0.1%{prerelease}%{dist}", "0.1%{prerelease}", "%{dist}", None),
        ("%{_short_release}%{?dist}.20", "%{_short_release}", "%{?dist}", 20),
        ("28%dist", "28", "%dist", None),
        ("%{release_string}", "%{release_string}", None, None),
    ],
)
def test_split_raw_release(raw_release, release, dist, minorbump):
    assert Specfile._split_raw_release(raw_release) == (release, dist, minorbump)


@pytest.mark.parametrize(
    "raw_release, release, result",
    [
        ("1%{?dist}", "28", "28%{?dist}"),
        ("0.1%{prerelease}%{dist}", "1", "1%{dist}"),
        ("%{_short_release}%{?dist}.20", "3", "3%{?dist}"),
        ("28%dist", "0.1", "0.1%dist"),
        ("%{release_string}", "1", "1"),
    ],
)
def test_get_updated_release(raw_release, release, result):
    assert Specfile._get_updated_release(raw_release, release) == result


@pytest.mark.parametrize(
    "release, bumped_release",
    [
        ("1%{?dist}", "2%{?dist}"),
        ("0.1%{?dist}", "0.2%{?dist}"),
        ("%release_func 26", "%release_func 27"),
        ("0.24.rc1%{?dist}", "0.25.rc1%{?dist}"),
        ("0.2.%{prerel}%{?dist}", "0.3.%{prerel}%{?dist}"),
        (
            "0.8.%{commitdate}%{shortcommit}%{?dist}",
            "0.9.%{commitdate}%{shortcommit}%{?dist}",
        ),
        (
            "3.%{git_date}git%{git_commit_short}%{?dist}",
            "4.%{git_date}git%{git_commit_short}%{?dist}",
        ),
        ("1%{?rcrel}%{?dist}.1", "1%{?rcrel}%{?dist}.2"),
        (
            "%{?beta_ver:0.}%{fedora_rel}%{?beta_ver:.%beta_ver}%{?dist}%{flagrel}%{?extrarel}",
            "%{?beta_ver:0.}%{fedora_rel}%{?beta_ver:.%beta_ver}%{?dist}%{flagrel}%{?extrarel}.1",
        ),
        ("4.rc2%{?dist}", "4.rc2%{?dist}.1"),
    ],
)
def test_bump_release_string(release, bumped_release):
    assert Specfile._bump_release_string(release) == bumped_release
