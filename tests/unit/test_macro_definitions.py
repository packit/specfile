# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from specfile.macro_definitions import MacroDefinition, MacroDefinitions


def test_find():
    macro_definitions = MacroDefinitions(
        [
            MacroDefinition("gitdate", "20160901", True, ("", " ", "     ", "")),
            MacroDefinition(
                "commit",
                "9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
                True,
                ("", " ", "      ", ""),
            ),
            MacroDefinition(
                "shortcommit", "%(c=%{commit}; echo ${c:0:7})", True, ("", " ", " ", "")
            ),
        ]
    )
    assert macro_definitions.find("gitdate") == 0
    assert macro_definitions.find("shortcommit") == 2
    with pytest.raises(ValueError):
        macro_definitions.find("gittag")


def test_get():
    macro_definitions = MacroDefinitions(
        [
            MacroDefinition("gitdate", "20160901", True, ("", " ", "     ", "")),
            MacroDefinition(
                "commit",
                "9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
                True,
                ("", " ", "      ", ""),
            ),
            MacroDefinition(
                "shortcommit", "%(c=%{commit}; echo ${c:0:7})", True, ("", " ", " ", "")
            ),
        ]
    )
    assert (
        macro_definitions.get("commit").body
        == "9ab9717cf7d1be1a85b165a8eacb71b9e5831113"
    )
    with pytest.raises(ValueError):
        macro_definitions.get("gittag")


def test_parse():
    macro_definitions = MacroDefinitions.parse(
        [
            "%global gitdate     20160901",
            "%global commit      9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
            "%global shortcommit %(c=%{commit}; echo ${c:0:7})",
            "",
            "Name:           test",
            "Version:        0.1.0",
            "",
            "%define desc(x) Test spec file containing several \\",
            "macro definitions in various formats (%?1)",
        ]
    )
    assert macro_definitions[0].name == "gitdate"
    assert macro_definitions[1].name == "commit"
    assert macro_definitions.commit.body == "9ab9717cf7d1be1a85b165a8eacb71b9e5831113"
    assert macro_definitions[2].name == "shortcommit"
    assert macro_definitions[-1].name == "desc(x)"
    assert macro_definitions[-1].body == (
        "Test spec file containing several \n"
        "macro definitions in various formats (%?1)"
    )


def test_get_raw_data():
    macro_definitions = MacroDefinitions(
        [
            MacroDefinition("gitdate", "20160901", True, ("", " ", "     ", "")),
            MacroDefinition(
                "commit",
                "9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
                True,
                ("", " ", "      ", ""),
            ),
            MacroDefinition(
                "shortcommit", "%(c=%{commit}; echo ${c:0:7})", True, ("", " ", " ", "")
            ),
            MacroDefinition(
                "desc(x)",
                "Test spec file containing several \nmacro definitions in various formats (%?1)",
                False,
                ("", " ", " ", ""),
                [
                    "",
                    "Name:           test",
                    "Version:        0.1.0",
                    "",
                ],
            ),
        ]
    )
    assert macro_definitions.get_raw_data() == [
        "%global gitdate     20160901",
        "%global commit      9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
        "%global shortcommit %(c=%{commit}; echo ${c:0:7})",
        "",
        "Name:           test",
        "Version:        0.1.0",
        "",
        "%define desc(x) Test spec file containing several \\",
        "macro definitions in various formats (%?1)",
    ]
