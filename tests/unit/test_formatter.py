# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import textwrap

import pytest

from specfile.formatter import format_expression


@pytest.mark.parametrize(
    "original, reformatted",
    [
        ("func('arg')", "func('arg')"),
        ("func('arg1', \"arg2\")", "func('arg1', 'arg2')"),
        ("func('arg1', 'arg\\'2')", "func('arg1', \"arg'2\")"),
        ("func('arg', kwarg='val')", "func('arg', kwarg='val')"),
        ("(None)", "None"),
        ("(None,)", "(None,)"),
        ("('a',\"b\",3)", "('a', 'b', 3)"),
        ("[1,2,3,4]", "[1, 2, 3, 4]"),
        ("{'key':'val'}", "{'key': 'val'}"),
        ("<ENUM_ITEM_1: 1>", "<ENUM_ITEM_1: 1>"),
        (
            "func1('first argument', True, func2(kwarg={42: ['nested list item 1', "
            "'nested list item 2', 'nested list item 3']}), 0, indent='    ', "
            "spec=<rpm.spec object at 0x7fe1ae1a6b30>)",
            textwrap.dedent(
                """\
                func1(
                    'first argument',
                    True,
                    func2(
                        kwarg={
                            42: [
                                'nested list item 1',
                                'nested list item 2',
                                'nested list item 3',
                            ],
                        },
                    ),
                    0,
                    indent='    ',
                    spec=<rpm.spec object at 0x7fe1ae1a6b30>,
                )"""
            ),
        ),
    ],
)
def test_format_expression(original, reformatted):
    assert format_expression(original) == reformatted
