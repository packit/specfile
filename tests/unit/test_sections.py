# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy

import pytest
from flexmock import flexmock

from specfile.macro_definitions import MacroDefinitions
from specfile.options import Options, Token, TokenType
from specfile.sections import Section, Sections


def test_find():
    sections = Sections(
        [
            Section("package"),
            Section("prep"),
            Section("changelog"),
            Section("pAckage", Options([Token(TokenType.DEFAULT, "foo")]), " "),
        ]
    )
    assert sections.find("prep") == 1
    assert sections.find("package foo") == 3
    with pytest.raises(ValueError):
        sections.find("install")


def test_get():
    sections = Sections(
        [
            Section("package"),
            Section("package", Options([Token(TokenType.DEFAULT, "bar")]), " "),
        ]
    )
    assert sections.get("package") == []
    assert sections.get("package bar") == []
    with pytest.raises(ValueError):
        sections.get("package foo")


@pytest.mark.parametrize(
    "id, existing, name, options, content",
    [
        (
            "package",
            True,
            "package",
            "",
            ["Name: test", "Version: 0.1", "Release: 1%{?dist}", ""],
        ),
        ("prep", True, "prep", "", ["%autosetup", ""]),
        ("package -n subpkg1", True, "package", "-n subpkg1", [""]),
        ("package -n subpkg2", False, "package", "-n subpkg2", []),
    ],
)
def test_get_or_create(id, existing, name, options, content):
    sections = Sections.parse(
        [
            "Name: test",
            "Version: 0.1",
            "Release: 1%{?dist}",
            "",
            "%description",
            "Test package",
            "",
            "%prep",
            "%autosetup",
            "",
            "%package -n subpkg1",
            "",
            "%changelog",
        ]
    )
    section = sections.get_or_create(id)
    assert section.name == name
    assert str(section.options) == options
    assert list(section) == content
    if not existing:
        assert section == sections[-1]


def test_parse():
    sections = Sections.parse(
        [
            "0",
            "",
            "",
            "%description  %{desc}",
            "",
            "%prep",
            "0",
            "1",
            "2",
            "",
            "%description x %{desc}",
            "",
            "%package %{subpkg}",
            "",
            "%package x",
            "%files y",
            "0",
            "%changelog",
        ],
        context=flexmock(expand=lambda s, **_: "\n" if s == "%{desc}" else ""),
    )
    assert sections[0][0] == "0"
    assert sections[1].id == "description"
    assert sections.description == ["%{desc}", ""]
    assert sections[2].id == "prep"
    assert sections.prep == ["0", "1", "2", ""]
    assert sections[3].id == "description x"
    assert sections[3] == ["%{desc}", ""]
    assert sections[4].id == "package %{subpkg}"
    assert sections[4] == [""]
    assert sections[5].id == "package x"
    assert not sections[5]
    assert sections[-1].id == "changelog"


def test_parse_case_insensitive():
    sections = Sections.parse(
        ["0", "", "%Prep", "0", "1", "2", "", "%pAckage x", "Requires: bar"]
    )
    assert sections[0][0] == "0"
    assert sections[1].id == "Prep"
    assert sections.prep == ["0", "1", "2", ""]
    assert sections[2].id == "pAckage x"
    assert sections[2] == ["Requires: bar"]


def test_parse_invalid_name():
    sections = Sections.parse(
        [
            "%description",
            "This is a description.",
            "",
            "%description(fr)",
            "Ceci est une description.",
            "",
        ]
    )
    assert len(sections) == 2  # including empty preamble
    assert sections[1].id == "description"
    assert sections.description[2] == "%description(fr)"


def test_parse_macro_definitions():
    lines = [
        "%package -n test",
        "Summary: Subpackage test",
        "",
        "%description -n test",
        "Subpackage test.",
        "",
        "%define template1()\\",
        "%package -n %{1}\\",
        "Summary: Subpackage %{1}\\",
        "\\",
        "%description -n %{1}\\",
        "Subpackage %{1}.",
        "",
        "%define template2() %{expand:",
        "%package -n %{1}",
        "Summary: Subpackage %{1}",
        "",
        "%description -n %{1}",
        "Subpackage %{1}.}",
        "",
        "%prep",
        "%autosetup",
    ]
    sections = Sections.parse(lines)
    assert len(sections) == 4
    assert sections[1].id == "package -n test"
    assert sections[-1].id == "prep"
    sections = Sections.parse(lines, MacroDefinitions.parse(lines))
    assert len(sections) == 4
    assert sections[1].id == "package -n test"
    assert sections[-1].id == "prep"


def test_get_raw_data():
    sections = Sections(
        [
            Section("package", data=["0", "", ""]),
            Section("description", separator="  ", data=["%{desc}", ""]),
            Section("prep", data=["0", "1", "2", ""]),
            Section(
                "description",
                Options([Token(TokenType.DEFAULT, "x")]),
                " ",
                " ",
                ["%{desc}", ""],
            ),
            Section(
                "package",
                Options([Token(TokenType.DEFAULT, "%{subpkg}")]),
                " ",
                data=[""],
            ),
            Section("package", Options([Token(TokenType.DEFAULT, "x")]), " "),
            Section("files", Options([Token(TokenType.DEFAULT, "y")]), " ", data=["0"]),
            Section("changelog"),
        ],
    )
    assert sections.get_raw_data() == [
        "0",
        "",
        "",
        "%description  %{desc}",
        "",
        "%prep",
        "0",
        "1",
        "2",
        "",
        "%description x %{desc}",
        "",
        "%package %{subpkg}",
        "",
        "%package x",
        "%files y",
        "0",
        "%changelog",
    ]


def test_copy_sections():
    sections = Sections([Section("package", data=["Name: test", "Version: 0.1"])])
    shallow_copy = copy.copy(sections)
    assert shallow_copy == sections
    assert shallow_copy is not sections
    assert shallow_copy[0] is sections[0]
    deep_copy = copy.deepcopy(sections)
    assert deep_copy == sections
    assert deep_copy is not sections
    assert deep_copy[0] is not sections[0]


@pytest.mark.parametrize(
    "section, is_script",
    [
        ("package", False),
        ("install", True),
        ("PostUn", True),
        ("SourceList", False),
    ],
)
def test_is_script(section, is_script):
    assert Section(section).is_script == is_script
