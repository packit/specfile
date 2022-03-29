# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import shutil

import pytest

from tests.constants import (
    SPEC_MINIMAL,
    SPEC_MULTIPLE_SOURCES,
    SPEC_PATCHLIST,
    SPECFILE,
)


@pytest.fixture(scope="function")
def spec_minimal(tmp_path):
    specfile_path = tmp_path / SPECFILE
    shutil.copyfile(SPEC_MINIMAL / SPECFILE, specfile_path)
    return specfile_path


@pytest.fixture(scope="function")
def spec_patchlist(tmp_path):
    destination = tmp_path / "spec_patchlist"
    shutil.copytree(SPEC_PATCHLIST, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_multiple_sources(tmp_path):
    destination = tmp_path / "spec_multiple_sources"
    shutil.copytree(SPEC_MULTIPLE_SOURCES, destination)
    return destination / SPECFILE
