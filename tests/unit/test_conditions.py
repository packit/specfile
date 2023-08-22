# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

import specfile.conditions
from specfile.conditions import process_conditions


@pytest.mark.parametrize(
    "lines, validity, resolve_func",
    [
        (
            ["%ifarch %{power64}", "export ARCH=PPC64", "%endif"],
            [True, True, True],
            lambda kwd, exp: True,
        ),
        (
            ["%ifarch %{power64}", "export ARCH=PPC64", "%endif"],
            [True, False, True],
            lambda kwd, exp: False,
        ),
        (
            [
                "%if 0%{?fedora} > 38",
                "Patch0: fedora.patch",
                "%elif 0%{?rhel} > 8",
                "Patch0: rhel.patch",
                "%else",
                "Patch0: unsupported.patch",
                "%endif",
            ],
            [True, False, True, True, True, False, True],
            lambda kwd, exp: "rhel" in exp,
        ),
        (
            [
                "%if %{with_gui}",
                "BuildRequires: libX11-devel",
                "%if 0%{?fedora}",
                "Requires: desktop-file-utils",
                "%endif",
                "BuildRequires: libXext-devel",
                "%else",
                "%if %{with_curses}",
                "BuildRequires: ncurses-devel",
                "%endif",
                "%global GUI 0",
                "%endif",
            ],
            [
                True,
                False,
                False,
                False,
                False,
                False,
                True,
                True,
                False,
                True,
                True,
                True,
            ],
            lambda kwd, exp: "fedora" in exp,
        ),
    ],
)
def test_process_conditions(lines, validity, resolve_func):
    def resolve_expression(kwd, exp, *_, **__):
        return resolve_func(kwd, exp)

    flexmock(specfile.conditions).should_receive("resolve_expression").replace_with(
        resolve_expression
    )
    processed_lines, processed_validity = zip(*process_conditions(lines))
    assert list(processed_lines) == lines
    assert list(processed_validity) == validity
