# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy

import pytest

from specfile.options import Options, Token, TokenType
from specfile.prep import AutosetupMacro, PatchMacro, Prep, PrepMacros, SetupMacro
from specfile.sections import Section


@pytest.mark.parametrize(
    "name, options, number",
    [
        ("%patch2", "-p1", 2),
        ("%patch0028", "-p2", 28),
        ("%patch", "-p1", 0),
        ("%patch", "-P1", 1),
        ("%patch3", "-P5", 5),
    ],
)
def test_patch_macro_number(name, options, number):
    macro = PatchMacro(
        name, Options(Options.tokenize(options), PatchMacro.OPTSTRING), " "
    )
    assert macro.number == number


def test_prep_macros_find():
    macros = PrepMacros(
        [
            SetupMacro("%setup", Options([]), ""),
            PatchMacro("%patch0", Options([]), ""),
        ]
    )
    assert macros.find("%patch0") == 1
    with pytest.raises(ValueError):
        macros.find("%autosetup")


@pytest.mark.parametrize(
    "lines_before, number, options, lines_after",
    [
        (
            ["%setup -q"],
            0,
            dict(p=1),
            ["%setup -q", "%patch0 -p1"],
        ),
        (
            ["%setup -q", "%patch0 -p1"],
            0,
            dict(p=2),
            ["%setup -q", "%patch0 -p1", "%patch0 -p2"],
        ),
        (
            ["%setup -q", "%patch999 -p1"],
            28,
            dict(p=1),
            ["%setup -q", "%patch28 -p1", "%patch999 -p1"],
        ),
        (
            ["%setup -q", "%patch999 -p1"],
            1001,
            dict(p=1),
            ["%setup -q", "%patch999 -p1", "%patch1001 -p1"],
        ),
        (
            ["%setup -q", "%{!?skip_first_patch:%patch0 -p1}", "%patch999 -p1"],
            28,
            dict(p=2, b=".patch28"),
            [
                "%setup -q",
                "%{!?skip_first_patch:%patch0 -p1}",
                "%patch28 -p2 -b .patch28",
                "%patch999 -p1",
            ],
        ),
    ],
)
def test_prep_add_patch_macro(lines_before, number, options, lines_after):
    prep = Prep.parse(Section("prep", data=lines_before))
    prep.add_patch_macro(number, **options)
    assert prep.get_raw_section_data() == lines_after


@pytest.mark.parametrize(
    "lines_before, number, lines_after",
    [
        (
            ["%setup -q", "%patch0 -p1", "%patch1 -p1", "%patch2 -p1"],
            1,
            ["%setup -q", "%patch0 -p1", "%patch2 -p1"],
        ),
        (
            ["%setup -q", "%{!?skip_first_patch:%patch0 -p1}", "%patch1 -p1"],
            0,
            ["%setup -q", "%patch1 -p1"],
        ),
    ],
)
def test_prep_remove_patch_macro(lines_before, number, lines_after):
    prep = Prep.parse(Section("prep", data=lines_before))
    prep.remove_patch_macro(number)
    assert prep.get_raw_section_data() == lines_after


def test_prep_parse():
    prep = Prep.parse(
        Section(
            "prep",
            data=[
                "%setup -q",
                "# a comment",
                "%patch0 -p1",
                "%{!?skip_patch2:%patch2 -p2}",
                "",
            ],
        )
    )
    assert prep.macros[0].name == "%setup"
    assert prep.macros[0].options.q
    assert prep.macros[1].name == "%patch0"
    assert prep.macros[1].options.p == 1
    assert prep.patch2.options.p == 2


def test_prep_get_raw_section_data():
    prep = Prep(
        PrepMacros(
            [
                SetupMacro(
                    SetupMacro.CANONICAL_NAME,
                    Options(
                        [Token(TokenType.DEFAULT, "-q")],
                        SetupMacro.OPTSTRING,
                        SetupMacro.DEFAULTS,
                    ),
                    " ",
                ),
                PatchMacro(
                    PatchMacro.CANONICAL_NAME + "0",
                    Options(
                        [Token(TokenType.DEFAULT, "-p1")],
                        PatchMacro.OPTSTRING,
                        PatchMacro.DEFAULTS,
                    ),
                    " ",
                    preceding_lines=["# a comment"],
                ),
                PatchMacro(
                    PatchMacro.CANONICAL_NAME + "2",
                    Options(
                        [Token(TokenType.DEFAULT, "-p2")],
                        PatchMacro.OPTSTRING,
                        PatchMacro.DEFAULTS,
                    ),
                    " ",
                    "%{!?skip_patch2:",
                    "}",
                ),
            ],
            [""],
        )
    )
    assert prep.get_raw_section_data() == [
        "%setup -q",
        "# a comment",
        "%patch0 -p1",
        "%{!?skip_patch2:%patch2 -p2}",
        "",
    ]


def test_copy_prep():
    prep = Prep(
        PrepMacros(
            [
                AutosetupMacro(
                    AutosetupMacro.CANONICAL_NAME,
                    Options([]),
                    "",
                ),
            ],
        )
    )
    shallow_copy = copy.copy(prep)
    assert shallow_copy == prep
    assert shallow_copy is not prep
    assert shallow_copy.macros is prep.macros
    assert shallow_copy.macros[0] is prep.macros[0]
    deep_copy = copy.deepcopy(prep)
    assert deep_copy == prep
    assert deep_copy is not prep
    assert deep_copy.macros is not prep.macros
    assert deep_copy.macros[0] is not prep.macros[0]
