# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path


def pytest_addoption(parser):
    parser.addoption(
        "--specdir",
        action="store",
        default=None,
        help="path to a directory containing spec files",
    )


def pytest_generate_tests(metafunc):
    if "spec_path" in metafunc.fixturenames:
        specdir = metafunc.config.getoption("specdir")
        specs = list(Path(specdir).glob("*.spec")) if specdir else []
        metafunc.parametrize("spec_path", specs, ids=lambda p: p.name)
