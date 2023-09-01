# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from specfile import Specfile


@pytest.mark.fail_slow(30)
def test_parse_texlive_spec():
    spec = Specfile("/tmp/texlive.spec")
    assert spec.expanded_version
