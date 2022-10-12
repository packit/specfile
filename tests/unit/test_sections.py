# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy

import pytest

from specfile.sections import Section, Sections


def test_find():
    sections = Sections(
        [
            Section("package"),
            Section("prep"),
            Section("changelog"),
            Section("pAckage foo"),
        ]
    )
    assert sections.find("prep") == 1
    assert sections.find("package foo") == 3
    with pytest.raises(ValueError):
        sections.find("install")


def test_get():
    sections = Sections([Section("package"), Section("package bar")])
    assert sections.get("package") == []
    assert sections.get("package bar") == []
    with pytest.raises(ValueError):
        sections.get("package foo")


def test_parse():
    sections = Sections.parse(
        [
            "0",
            "",
            "",
            "%prep",
            "0",
            "1",
            "2",
            "",
            "%package x",
            "%files y",
            "0",
            "%changelog",
        ]
    )
    assert sections[0][0] == "0"
    assert sections[1].name == "prep"
    assert sections.prep == ["0", "1", "2", ""]
    assert sections[2].name == "package x"
    assert not sections[2]
    assert sections[-1].name == "changelog"


def test_parse_case_insensitive():
    sections = Sections.parse(
        ["0", "", "%Prep", "0", "1", "2", "", "%pAckage x", "Requires: bar"]
    )
    assert sections[0][0] == "0"
    assert sections[1].name == "Prep"
    assert sections.prep == ["0", "1", "2", ""]
    assert sections[2].name == "pAckage x"
    assert sections[2] == ["Requires: bar"]


def test_copy_sections():
    sections = Sections([Section("package"), Section("package bar")])
    sections_copy = copy.deepcopy(sections)
    assert sections == sections_copy
