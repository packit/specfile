# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
import io
import shutil

import pytest

from specfile import Specfile
from tests.constants import (
    SPEC_AUTOPATCH,
    SPEC_AUTOSETUP,
    SPEC_COMMENTED_PATCHES,
    SPEC_CONDITIONALIZED_CHANGELOG,
    SPEC_CONDITIONALIZED_VERSION,
    SPEC_INCLUDES,
    SPEC_MACROS,
    SPEC_MINIMAL,
    SPEC_MULTIPLE_SOURCES,
    SPEC_NO_TRAILING_NEWLINE,
    SPEC_PATCHLIST,
    SPEC_PRERELEASE,
    SPEC_PRERELEASE2,
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
def spec_prerelease(tmp_path):
    destination = tmp_path / "spec_prerelease"
    shutil.copytree(SPEC_PRERELEASE, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_prerelease2(tmp_path):
    destination = tmp_path / "spec_prerelease2"
    shutil.copytree(SPEC_PRERELEASE2, destination)
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


@pytest.fixture(scope="function")
def spec_no_trailing_newline(tmp_path):
    destination = tmp_path / "spec_no_trailing_newline"
    shutil.copytree(SPEC_NO_TRAILING_NEWLINE, destination)
    return destination / SPECFILE


@pytest.fixture(scope="function")
def spec_conditionalized_changelog(tmp_path):
    specfile_path = tmp_path / SPECFILE
    shutil.copyfile(SPEC_CONDITIONALIZED_CHANGELOG / SPECFILE, specfile_path)
    return specfile_path


@pytest.fixture(scope="function")
def spec_conditionalized_version(tmp_path):
    specfile_path = tmp_path / SPECFILE
    shutil.copyfile(SPEC_CONDITIONALIZED_VERSION / SPECFILE, specfile_path)
    return specfile_path


@pytest.fixture(
    params=[
        "file_path",
        "text_file",
        "binary_file",
        "text_io_stream",
        "binary_io_stream",
        "content_string",
    ]
)
def specfile_factory(request):
    """
    pytest fixture to create a `Specfile` instance with different input modes.

    Returns:
        Function that creates a `Specfile` instance.
    """
    mode = request.param

    def _create_specfile(input_path, **kwargs):
        kwargs.setdefault("sourcedir", input_path.parent)

        if mode == "file_path":
            return Specfile(path=input_path, **kwargs)
        elif mode == "text_file":
            f = open(input_path, "r+", **Specfile.ENCODING_ARGS)
            return Specfile(file=f, **kwargs)
        elif mode == "binary_file":
            f = open(input_path, "rb+")
            return Specfile(file=f, **kwargs)
        elif mode == "text_io_stream":
            content = input_path.read_text(**Specfile.ENCODING_ARGS)
            return Specfile(file=io.StringIO(content), **kwargs)
        elif mode == "binary_io_stream":
            content = input_path.read_bytes()
            return Specfile(file=io.BytesIO(content), **kwargs)
        elif mode == "content_string":
            content = input_path.read_text(**Specfile.ENCODING_ARGS)
            return Specfile(content=content, **kwargs)

    return _create_specfile
