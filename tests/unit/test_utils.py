# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from specfile.utils import get_filename_from_location


@pytest.mark.parametrize(
    "location, filename",
    [
        ("", ""),
        ("tarball-0.1.tar.gz", "tarball-0.1.tar.gz"),
        ("https://example.com", ""),
        ("https://example.com/archive/tarball-0.1.tar.gz", "tarball-0.1.tar.gz"),
        (
            "https://example.com/archive/tarball-0.1.tar.gz#fragment",
            "tarball-0.1.tar.gz#fragment",
        ),
        (
            "https://example.com/download_tarball.cgi#/tarball-0.1.tar.gz",
            "tarball-0.1.tar.gz",
        ),
        (
            "https://example.com/tarball-latest.tar.gz#/file=tarball-0.1.tar.gz",
            "tarball-0.1.tar.gz",
        ),
    ],
)
def test_get_filename_from_location(location, filename):
    assert get_filename_from_location(location) == filename
