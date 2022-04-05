# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from argparse import Namespace as NS

import pytest

from specfile.prep import AutopatchMacro, AutosetupMacro, PatchMacro, Prep, SetupMacro
from specfile.sections import Section


@pytest.mark.parametrize(
    "cls, optstr, options",
    [
        (
            SetupMacro,
            "-q -n %{srcname}-%{version}",
            NS(
                n="%{srcname}-%{version}",
                q=True,
                c=False,
                D=False,
                T=False,
                b=None,
                a=None,
            ),
        ),
        (
            SetupMacro,
            "-T -a1",
            NS(n="%{name}-%{version}", q=False, c=False, D=False, T=True, b=None, a=1),
        ),
        (PatchMacro, "-p1 -b .patch1", NS(P=None, p=1, b=".patch1", E=False)),
        (PatchMacro, "-P 28 -E", NS(P=28, p=None, b=None, E=True)),
        (
            AutosetupMacro,
            "-p1 -v",
            NS(
                n="%{name}-%{version}",
                v=True,
                c=False,
                D=False,
                T=False,
                b=None,
                a=None,
                N=False,
                S="patch",
                p=1,
            ),
        ),
        (
            AutosetupMacro,
            "-Sgit -p 2",
            NS(
                n="%{name}-%{version}",
                v=False,
                c=False,
                D=False,
                T=False,
                b=None,
                a=None,
                N=False,
                S="git",
                p=2,
            ),
        ),
        (
            AutopatchMacro,
            "-p1 -m 100 -M 199",
            NS(v=False, p=1, m=100, M=199, indices=[]),
        ),
        (
            AutopatchMacro,
            "-p2 -v 3 4 7",
            NS(v=True, p=2, m=None, M=None, indices=[3, 4, 7]),
        ),
    ],
)
def test_prep_macro_parse_options(cls, optstr, options):
    macro = cls(cls.CANONICAL_NAME, 0)
    macro._parse_options(optstr)
    assert macro.options == options


@pytest.mark.parametrize(
    "name, optstr, index",
    [
        ("%patch2", "-p1", 2),
        ("%patch0028", "-p2", 28),
        ("%patch", "-p1", 0),
        ("%patch", "-P1", 1),
        ("%patch3", "-P5", 5),
    ],
)
def test_patch_macro_index(name, optstr, index):
    macro = PatchMacro(name, 0)
    macro._parse_options(optstr)
    assert macro.index == index


@pytest.mark.parametrize(
    "lines_before, index, options, lines_after",
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
            dict(p=3),
            ["%setup -q", "%patch0 -p3", "%patch0 -p1"],
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
            ["%setup -q", "%{?!skip_first_patch:%patch0 -p1}", "%patch999 -p1"],
            28,
            dict(p=2, b=".patch28"),
            [
                "%setup -q",
                "%{?!skip_first_patch:%patch0 -p1}",
                "%patch28 -p2 -b .patch28",
                "%patch999 -p1",
            ],
        ),
    ],
)
def test_prep_add_patch_macro(lines_before, index, options, lines_after):
    section = Section("prep", lines_before)
    Prep(section).add_patch_macro(index, **options)
    assert section == Section("prep", lines_after)


@pytest.mark.parametrize(
    "lines_before, index, lines_after",
    [
        (
            ["%setup -q", "%patch0 -p1", "%patch1 -p1", "%patch2 -p1"],
            1,
            ["%setup -q", "%patch0 -p1", "%patch2 -p1"],
        ),
        (
            ["%setup -q", "%{?!skip_first_patch:%patch0 -p1}", "%patch1 -p1"],
            0,
            ["%setup -q", "%patch1 -p1"],
        ),
    ],
)
def test_prep_remove_patch_macro(lines_before, index, lines_after):
    section = Section("prep", lines_before)
    Prep(section).remove_patch_macro(index)
    assert section == Section("prep", lines_after)
