# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from specfile.options import Options, Positionals, Token, TokenType


@pytest.mark.parametrize(
    "optstring, tokens, result",
    [
        (
            "vp:m:M:",
            [
                Token(TokenType.DEFAULT, "28"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DOUBLE_QUOTED, "test arg"),
            ],
            [0, 2],
        ),
        (
            "vp:m:M:",
            [
                Token(TokenType.DEFAULT, "-p"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "1"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-v"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "28"),
            ],
            [6],
        ),
        (
            "vp:m:M:",
            [
                Token(TokenType.DEFAULT, "-m"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "10"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "test"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-M"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "20"),
            ],
            [4],
        ),
    ],
)
def test_positionals_get_items(optstring, tokens, result):
    options = Options(tokens, optstring)
    assert Positionals(options)._get_items() == result


@pytest.mark.parametrize(
    "optstring, tokens, index, value, tokens_index, token_type",
    [
        (
            "vp:m:M:",
            [
                Token(TokenType.DEFAULT, "-p1"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "test"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "28"),
            ],
            0,
            "test arg",
            2,
            TokenType.DOUBLE_QUOTED,
        ),
        (
            "vp:m:M:",
            [
                Token(TokenType.DEFAULT, "-p1"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "test"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "28"),
            ],
            1,
            123,
            4,
            TokenType.DEFAULT,
        ),
        (
            "vp:m:M:",
            [],
            0,
            "test",
            0,
            TokenType.DEFAULT,
        ),
    ],
)
def test_positionals_insert(optstring, tokens, index, value, tokens_index, token_type):
    options = Options(tokens, optstring)
    positionals = Positionals(options)
    positionals.insert(index, value)
    assert options._tokens[tokens_index].type == token_type
    assert options._tokens[tokens_index].value == str(value)


@pytest.mark.parametrize(
    "optstring, option, valid",
    [
        ("a:b:cDn:Tq", "a", True),
        ("a:b:cDn:Tq", "q", True),
        ("a:b:cDn:Tq", "v", False),
    ],
)
def test_options_valid_option(optstring, option, valid):
    options = Options([], optstring)
    assert options._valid_option(option) == valid


@pytest.mark.parametrize(
    "optstring, option, requires_argument",
    [
        ("a:b:cDn:Tq", "a", True),
        ("a:b:cDn:Tq", "q", False),
        ("a:b:cDn:Tq", "v", None),
    ],
)
def test_options_requires_argument(optstring, option, requires_argument):
    options = Options([], optstring)
    if option in optstring:
        assert options._requires_argument(option) == requires_argument
    else:
        with pytest.raises(ValueError):
            options._requires_argument(option)


@pytest.mark.parametrize(
    "optstring, tokens, option, result",
    [
        (
            "P:p:REb:z:F:d:o:Z",
            [
                Token(TokenType.DEFAULT, "-p1"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-b"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, ".test"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-E"),
            ],
            "p",
            (0, 0),
        ),
        (
            "P:p:REb:z:F:d:o:Z",
            [
                Token(TokenType.DEFAULT, "-p1"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-b"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, ".test"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-E"),
            ],
            "b",
            (2, 4),
        ),
        (
            "P:p:REb:z:F:d:o:Z",
            [
                Token(TokenType.DEFAULT, "-p1"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-b"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, ".test"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-E"),
            ],
            "E",
            (6, None),
        ),
        (
            "P:p:REb:z:F:d:o:Z",
            [
                Token(TokenType.DEFAULT, "-p1"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-b"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, ".test"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-E"),
            ],
            "F",
            (None, None),
        ),
    ],
)
def test_options_find_option(optstring, tokens, option, result):
    options = Options(tokens, optstring)
    assert options._find_option(option) == result


@pytest.mark.parametrize(
    "option_string, result",
    [
        (
            "-p1 -b .test -E",
            [
                Token(TokenType.DEFAULT, "-p1"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-b"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, ".test"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-E"),
            ],
        ),
        (
            "-p 28 -b .test\\ escape",
            [
                Token(TokenType.DEFAULT, "-p"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "28"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-b"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, ".test escape"),
            ],
        ),
        (
            '-b ".test \\"double quotes\\""',
            [
                Token(TokenType.DEFAULT, "-b"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DOUBLE_QUOTED, '.test "double quotes"'),
            ],
        ),
        (
            "-p1 -b .test_whitespace_at_the_end -M 2  ",
            [
                Token(TokenType.DEFAULT, "-p1"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-b"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, ".test_whitespace_at_the_end"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-M"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "2"),
                Token(TokenType.WHITESPACE, "  "),
            ],
        ),
        (
            '-q -n %{name}-%{version}%[%{rc}?"-rc":""]',
            [
                Token(TokenType.DEFAULT, "-q"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-n"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, '%{name}-%{version}%[%{rc}?"-rc":""]'),
            ],
        ),
        (
            "-q -n '%{name}-%{version}'",
            [
                Token(TokenType.DEFAULT, "-q"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-n"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.QUOTED, "%{name}-%{version}"),
            ],
        ),
        (
            '-q -n "%{name}-%{version}"',
            [
                Token(TokenType.DEFAULT, "-q"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-n"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DOUBLE_QUOTED, "%{name}-%{version}"),
            ],
        ),
        (
            '-q -n \'%{name}-%{version}%[%{rc}?"-rc":""]\'',
            [
                Token(TokenType.DEFAULT, "-q"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.DEFAULT, "-n"),
                Token(TokenType.WHITESPACE, " "),
                Token(TokenType.QUOTED, '%{name}-%{version}%[%{rc}?"-rc":""]'),
            ],
        ),
    ],
)
def test_options_tokenize(option_string, result):
    assert Options.tokenize(option_string) == result
