# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import tempfile
from pathlib import Path

import pytest

# define our own tmp_path fixture for older version of pytest (CentOS)
try:
    from _pytest import tmpdir

    _ = tmpdir.tmp_path
except (ImportError, AttributeError, KeyError):

    @pytest.fixture()
    def tmp_path():
        TMP_DIR = "/tmp/pytest_tmp_path/"
        Path(TMP_DIR).mkdir(exist_ok=True, parents=True)
        return Path(tempfile.mkdtemp(prefix=TMP_DIR))
