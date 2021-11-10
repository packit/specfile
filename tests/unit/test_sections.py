# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from specfile.sections import Sections, Section


def test_find():
    sections = Sections([Section("package"), Section("prep"), Section("changelog")])
    assert sections.find("prep") == 1
    with pytest.raises(ValueError):
        sections.find("install")


def test_parse():
    sections = Sections.parse(
        "0\n\n%prep\n0\n1\n2\n\n%package x\n%files y\n0\n%changelog"
    )
    assert sections[0][0] == "0"
    assert sections[1].name == "prep"
    assert sections.prep == ["0", "1", "2", ""]
    assert sections[2].name == "package x"
    assert not sections[2]
    assert sections[-1].name == "changelog"
