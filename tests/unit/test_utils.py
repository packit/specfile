# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from specfile.utils import EVR, NEVR, NEVRA, count_brackets, get_filename_from_location


@pytest.mark.parametrize(
    "location, filename",
    [
        ("", ""),
        ("tarball-0.1.tar.gz", "tarball-0.1.tar.gz"),
        ("https://example.com", "example.com"),
        ("https://example.com#fragment", "example.com#fragment"),
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


@pytest.mark.parametrize(
    "string, count",
    [
        ("", (0, 0)),
        ("%macro", (0, 0)),
        ("%{macro}", (0, 0)),
        ("%{{macro}}", (0, 0)),
        ("%{{macro}", (1, 0)),
        ("%{macro:", (1, 0)),
        ("%(echo %{v}", (0, 1)),
        ("%(echo %{v} | cut -d. -f3)", (0, 0)),
    ],
)
def test_count_brackets(string, count):
    assert count_brackets(string) == count


def test_EVR_compare():
    assert EVR(version="0") == EVR(version="0")
    assert EVR(version="0", release="1") != EVR(version="0", release="2")
    assert EVR(version="12.0", release="1") <= EVR(version="12.0", release="1")
    assert EVR(version="12.0", release="1") <= EVR(version="12.0", release="2")
    assert EVR(epoch=2, version="56.8", release="5") > EVR(
        epoch=1, version="99.2", release="2"
    )


def test_NEVR_compare():
    assert NEVR(name="test", version="1", release="1") == NEVR(
        name="test", version="1", release="1"
    )
    assert NEVR(name="test", version="3", release="1") != NEVR(
        name="test2", version="3", release="1"
    )
    with pytest.raises(TypeError):
        NEVR(name="test", version="3", release="1") > NEVR(
            name="test2", version="1", release="2"
        )


def test_NEVRA_compare():
    assert NEVRA(name="test", version="1", release="1", arch="x86_64") == NEVRA(
        name="test", version="1", release="1", arch="x86_64"
    )
    assert NEVRA(name="test", version="2", release="1", arch="x86_64") != NEVRA(
        name="test", version="2", release="1", arch="aarch64"
    )
    with pytest.raises(TypeError):
        NEVRA(name="test", version="1", release="1", arch="aarch64") < NEVRA(
            name="test", version="2", release="1", arch="x86_64"
        )


@pytest.mark.parametrize(
    "evr, result",
    [
        ("0", EVR(version="0")),
        ("12.0-1", EVR(version="12.0", release="1")),
        ("2:56.8-5", EVR(epoch=2, version="56.8", release="5")),
        ("0.8.0-1.fc37", EVR(version="0.8.0", release="1.fc37")),
        ("0.5.0~rc2-1.el9", EVR(version="0.5.0~rc2", release="1.el9")),
        ("7.3-0.2.rc1.fc38", EVR(version="7.3", release="0.2.rc1.fc38")),
        (
            "7.3~rc1^20200701gdeadf00f-12.fc38",
            EVR(version="7.3~rc1^20200701gdeadf00f", release="12.fc38"),
        ),
    ],
)
def test_EVR_from_string(evr, result):
    assert EVR.from_string(evr) == result


@pytest.mark.parametrize(
    "nevr, result",
    [
        ("package-0", NEVR(name="package", version="0")),
        ("package-12.0-1", NEVR(name="package", version="12.0", release="1")),
        (
            "package-2:56.8-5",
            NEVR(name="package", epoch=2, version="56.8", release="5"),
        ),
        (
            "package-0.8.0-1.fc37",
            NEVR(name="package", version="0.8.0", release="1.fc37"),
        ),
        (
            "package-0.5.0~rc2-1.el9",
            NEVR(name="package", version="0.5.0~rc2", release="1.el9"),
        ),
        (
            "package-devel-7.3-0.2.rc1.fc38",
            NEVR(name="package-devel", version="7.3", release="0.2.rc1.fc38"),
        ),
        (
            "package-7.3~rc1^20200701gdeadf00f-12.fc38",
            NEVR(
                name="package", version="7.3~rc1^20200701gdeadf00f", release="12.fc38"
            ),
        ),
    ],
)
def test_NEVR_from_string(nevr, result):
    assert NEVR.from_string(nevr) == result


@pytest.mark.parametrize(
    "nevra, result",
    [
        (
            "package-12.0-1.x86_64",
            NEVRA(name="package", version="12.0", release="1", arch="x86_64"),
        ),
        (
            "package-2:56.8-5.aarch64",
            NEVRA(name="package", epoch=2, version="56.8", release="5", arch="aarch64"),
        ),
        (
            "package-0.8.0-1.fc37.armv6hl",
            NEVRA(name="package", version="0.8.0", release="1.fc37", arch="armv6hl"),
        ),
        (
            "package-0.5.0~rc2-1.el9.noarch",
            NEVRA(name="package", version="0.5.0~rc2", release="1.el9", arch="noarch"),
        ),
        (
            "package-devel-7.3-0.2.rc1.fc38.i686",
            NEVRA(
                name="package-devel", version="7.3", release="0.2.rc1.fc38", arch="i686"
            ),
        ),
        (
            "package-7.3~rc1^20200701gdeadf00f-12.fc38.riscv",
            NEVRA(
                name="package",
                version="7.3~rc1^20200701gdeadf00f",
                release="12.fc38",
                arch="riscv",
            ),
        ),
    ],
)
def test_NEVRA_from_string(nevra, result):
    assert NEVRA.from_string(nevra) == result
