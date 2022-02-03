# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime
import shutil
import subprocess
from pathlib import Path

import pytest
from flexmock import flexmock

from specfile.exceptions import SpecfileException
from specfile.sections import Section
from specfile.specfile import Specfile

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"
SPECFILE = DATA_DIR / "test.spec"


@pytest.fixture(scope="function")
def specfile(tmp_path):
    specfile_path = tmp_path / "test.spec"
    shutil.copyfile(SPECFILE, specfile_path)
    return specfile_path


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
    specfile, rpmdev_packager_available, entry, author, email, timestamp, result
):
    if not rpmdev_packager_available:
        flexmock(subprocess).should_receive("check_output").with_args(
            "rpmdev-packager"
        ).and_raise(FileNotFoundError)
    elif author is None:
        flexmock(subprocess).should_receive("check_output").with_args(
            "rpmdev-packager"
        ).and_return(b"John Doe <john@doe.net>")
    spec = Specfile(specfile)
    if not rpmdev_packager_available:
        with pytest.raises(SpecfileException):
            spec.add_changelog_entry(entry, author, email, timestamp)
    else:
        spec.add_changelog_entry(entry, author, email, timestamp)
        with spec.sections() as sections:
            assert sections.changelog[: len(result)] == result
