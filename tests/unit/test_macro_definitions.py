# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy

import pytest

from specfile.macro_definitions import (
    CommentOutStyle,
    MacroDefinition,
    MacroDefinitions,
)


def test_find():
    macro_definitions = MacroDefinitions(
        [
            MacroDefinition(
                "gitdate",
                "20160901",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", "     ", ""),
            ),
            MacroDefinition(
                "commit",
                "9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", "      ", ""),
            ),
            MacroDefinition(
                "shortcommit",
                "%(c=%{commit}; echo ${c:0:7})",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", " ", ""),
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
            MacroDefinition(
                "gitdate",
                "20160901",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", "     ", ""),
            ),
            MacroDefinition(
                "commit",
                "9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", "      ", ""),
            ),
            MacroDefinition(
                "shortcommit",
                "%(c=%{commit}; echo ${c:0:7})",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", " ", ""),
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
            "%dnl %global pre         a1",
            "#global prerel      beta2",
            "# %%global prerelease pre3",
            "",
            "#%global seemingly_commented_out 1",
            "",
            "Name:           test",
            "Version:        0.1.0",
            "",
            "%define desc(x) Test spec file containing several \\",
            "macro definitions in various formats (%?1)",
            "",
            "%global trailing_newline \\",
            "body with trailing newline \\",
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
    assert macro_definitions[3].name == "pre"
    assert macro_definitions[3].commented_out
    assert macro_definitions[3].comment_out_style is CommentOutStyle.DNL
    assert macro_definitions[4].name == "prerel"
    assert macro_definitions[4].commented_out
    assert macro_definitions[4].comment_out_style is CommentOutStyle.HASH
    assert macro_definitions[5].name == "prerelease"
    assert macro_definitions[5].commented_out
    assert macro_definitions[5].comment_out_style is CommentOutStyle.OTHER
    assert macro_definitions[6].name == "seemingly_commented_out"
    assert not macro_definitions[6].commented_out
    assert macro_definitions[7].name == "desc(x)"
    assert macro_definitions[7].body == (
        "Test spec file containing several \\\n"
        "macro definitions in various formats (%?1)"
    )
    assert macro_definitions[8].name == "trailing_newline"
    assert macro_definitions[8].body == "\\\nbody with trailing newline \\\n"
    assert macro_definitions[8].is_global
    assert not macro_definitions[8].commented_out
    assert macro_definitions[8]._whitespace == ("", " ", " ", "")
    assert macro_definitions[8].valid
    assert macro_definitions[-1].name == "example()"
    assert macro_definitions[-1].body == (
        "%{expand:\n"
        "This an example of a macro definition with body \n"
        "spawning across mutiple lines}"
    )


def test_get_raw_data():
    macro_definitions = MacroDefinitions(
        [
            MacroDefinition(
                "gitdate",
                "20160901",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", "     ", ""),
            ),
            MacroDefinition(
                "commit",
                "9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", "      ", ""),
            ),
            MacroDefinition(
                "shortcommit",
                "%(c=%{commit}; echo ${c:0:7})",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", " ", ""),
            ),
            MacroDefinition(
                "pre",
                "a1",
                True,
                True,
                CommentOutStyle.DNL,
                ("", " ", "         ", ""),
                " ",
                True,
                [""],
            ),
            MacroDefinition(
                "prerel",
                "beta2",
                True,
                True,
                CommentOutStyle.HASH,
                ("", " ", "      ", ""),
            ),
            MacroDefinition(
                "prerelease",
                "pre3",
                True,
                True,
                CommentOutStyle.OTHER,
                ("", " ", " ", ""),
                "# %",
            ),
            MacroDefinition(
                "seemingly_commented_out",
                "1",
                True,
                False,
                CommentOutStyle.DNL,
                ("#", " ", " ", ""),
                "",
                True,
                [""],
            ),
            MacroDefinition(
                "desc(x)",
                "Test spec file containing several \\\nmacro definitions in various formats (%?1)",
                False,
                False,
                CommentOutStyle.DNL,
                ("", " ", " ", ""),
                "",
                True,
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
                False,
                CommentOutStyle.DNL,
                ("", " ", " ", ""),
                "",
                True,
                [""],
            ),
            MacroDefinition(
                "trailing_newline",
                "\\\nbody with trailing newline \\\n",
                True,
                False,
                CommentOutStyle.DNL,
                ("", " ", " ", ""),
            ),
        ]
    )
    assert macro_definitions.get_raw_data() == [
        "%global gitdate     20160901",
        "%global commit      9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
        "%global shortcommit %(c=%{commit}; echo ${c:0:7})",
        "",
        "%dnl %global pre         a1",
        "#global prerel      beta2",
        "# %%global prerelease pre3",
        "",
        "#%global seemingly_commented_out 1",
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
        "%global trailing_newline \\",
        "body with trailing newline \\",
        "",
    ]


def test_copy_macro_definitions():
    macro_definitions = MacroDefinitions(
        [
            MacroDefinition(
                "commit",
                "9ab9717cf7d1be1a85b165a8eacb71b9e5831113",
                True,
                False,
                CommentOutStyle.DNL,
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
