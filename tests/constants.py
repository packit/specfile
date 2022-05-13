# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"
SPEC_MINIMAL = DATA_DIR / "spec_minimal"
SPEC_RPMAUTOSPEC = DATA_DIR / "spec_rpmautospec"
SPEC_TRADITIONAL = DATA_DIR / "spec_traditional"
SPEC_AUTOSETUP = DATA_DIR / "spec_autosetup"
SPEC_AUTOPATCH = DATA_DIR / "spec_autopatch"
SPEC_PATCHLIST = DATA_DIR / "spec_patchlist"
SPEC_MULTIPLE_SOURCES = DATA_DIR / "spec_multiple_sources"

SPECFILE = "test.spec"
