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
