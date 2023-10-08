# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from specfile import Specfile


def test_parse(spec_path):
    spec = Specfile(spec_path, force_parse=True)
    assert spec.expanded_version
