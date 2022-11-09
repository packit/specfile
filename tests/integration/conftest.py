# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import shutil

import pytest

from tests.constants import (
    SPEC_AUTOPATCH,
    SPEC_AUTOSETUP,
    SPEC_COMMENTED_PATCHES,
    SPEC_INCLUDES,
    SPEC_MACROS,
    SPEC_MINIMAL,
    SPEC_MULTIPLE_SOURCES,
    SPEC_PATCHLIST,
    SPEC_RPMAUTOSPEC,
    SPEC_SHELL_EXPANSIONS,
    SPEC_TRADITIONAL,
    SPECFILE,
)


@pytest.fixture(scope="function")
def spec_minimal(tmp_path):
    specfile_path = tmp_path / SPECFILE
    shutil.copyfile(SPEC_MINIMAL / SPECFILE, specfile_path)
    return specfile_path


@pytest.fixture(scope="function")
def spec_rpmautospec(tmp_path):
    specfile_path = tmp_path / SPECFILE
    shutil.copyfile(SPEC_RPMAUTOSPEC / SPECFILE, specfile_path)
    return specfile_path


@pytest.fixture(scope="function")
def spec_traditional(tmp_path):
    destination = tmp_path / "spec_traditional"
    shutil.copytree(SPEC_TRADITIONAL, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_autosetup(tmp_path):
    destination = tmp_path / "spec_autosetup"
    shutil.copytree(SPEC_AUTOSETUP, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_autopatch(tmp_path):
    destination = tmp_path / "spec_autopatch"
    shutil.copytree(SPEC_AUTOPATCH, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_patchlist(tmp_path):
    destination = tmp_path / "spec_patchlist"
    shutil.copytree(SPEC_PATCHLIST, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_includes(tmp_path):
    destination = tmp_path / "spec_includes"
    shutil.copytree(SPEC_INCLUDES, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_macros(tmp_path):
    destination = tmp_path / "spec_macros"
    shutil.copytree(SPEC_MACROS, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_multiple_sources(tmp_path):
    destination = tmp_path / "spec_multiple_sources"
    shutil.copytree(SPEC_MULTIPLE_SOURCES, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_commented_patches(tmp_path):
    destination = tmp_path / "spec_commented_patches"
    shutil.copytree(SPEC_COMMENTED_PATCHES, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_shell_expansions(tmp_path):
    destination = tmp_path / "spec_shell_expansions"
    shutil.copytree(SPEC_SHELL_EXPANSIONS, destination)
    return destination / SPECFILE
