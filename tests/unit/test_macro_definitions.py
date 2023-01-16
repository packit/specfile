# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy

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
            "",
            "%define example() %{expand:",
            "This an example of a macro definition with body ",
            "spawning across mutiple lines}",
        ]
    )
    assert macro_definitions[0].name == "gitdate"
    assert macro_definitions[1].name == "commit"
    assert macro_definitions.commit.body == "9ab9717cf7d1be1a85b165a8eacb71b9e5831113"
    assert macro_definitions[2].name == "shortcommit"
    assert macro_definitions[3].name == "desc(x)"
    assert macro_definitions[3].body == (
        "Test spec file containing several \\\n"
        "macro definitions in various formats (%?1)"
    )
    assert macro_definitions[-1].name == "example()"
    assert macro_definitions[-1].body == (
        "%{expand:\n"
        "This an example of a macro definition with body \n"
        "spawning across mutiple lines}"
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
                "Test spec file containing several \\\nmacro definitions in various formats (%?1)",
                False,
                ("", " ", " ", ""),
                [
                    "",
                    "Name:           test",
                    "Version:        0.1.0",
                    "",
                ],
            ),
            MacroDefinition(
                "example()",
                "%{expand:\n"
                "This an example of a macro definition with body \n"
                "spawning across mutiple lines}",
                False,
                ("", " ", " ", ""),
                [""],
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
        "",
        "%define example() %{expand:",
        "This an example of a macro definition with body ",
        "spawning across mutiple lines}",
    ]


def test_copy_macro_definitions():
    macro_definitions = MacroDefinitions(
        [
            MacroDefinition(
                "commit",
                "9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
                True,
                ("", " ", "      ", ""),
            ),
        ],
    )
    shallow_copy = copy.copy(macro_definitions)
    assert shallow_copy == macro_definitions
    assert shallow_copy is not macro_definitions
    assert shallow_copy[0] is macro_definitions[0]
    deep_copy = copy.deepcopy(macro_definitions)
    assert deep_copy == macro_definitions
    assert deep_copy is not macro_definitions
    assert deep_copy[0] is not macro_definitions[0]
