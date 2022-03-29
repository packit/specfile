# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"
SPEC_MINIMAL = DATA_DIR / "spec_minimal"
SPEC_PATCHLIST = DATA_DIR / "spec_patchlist"
SPEC_MULTIPLE_SOURCES = DATA_DIR / "spec_multiple_sources"

SPECFILE = "test.spec"
