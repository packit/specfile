# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from specfile.conditions import process_conditions
from specfile.macro_definitions import MacroDefinitions
from specfile.macros import Macros


@pytest.mark.parametrize(
    "lines, validity, expand_func",
    [
        (
            ["%ifarch %{power64}", "export ARCH=PPC64", "%endif"],
            [True, True, True],
            lambda expr: (
                "ppc64"
                if expr == "%{_target_cpu}"
                else "ppc64 ppc64p7 ppc64le" if expr == "%{power64}" else expr
            ),
        ),
        (
            ["%ifarch %{power64}", "export ARCH=PPC64", "%endif"],
            [True, False, True],
            lambda expr: (
                "x86_64"
                if expr == "%{_target_cpu}"
                else "ppc64 ppc64p7 ppc64le" if expr == "%{power64}" else expr
            ),
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
            lambda expr: (
                "0"
                if expr == "%{expr:0%{?fedora} > 38}"
                else "1" if expr == "%{expr:0%{?rhel} > 8}" else expr
            ),
        ),
        (
            [
                "%if %{with_gui}",
                "BuildRequires: libX11-devel",
                "%if 0%{?fedora}",
                "Requires: desktop-file-utils",
                "%else",
                "Requires: gnome-desktop",
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
                False,
                False,
                True,
                True,
                False,
                True,
                True,
                True,
            ],
            lambda expr: (
                "0"
                if expr.startswith("%{expr:%{with_")
                else "1" if expr == "%{expr:0%{?fedora}}" else expr
            ),
        ),
        (
            [
                "%if %{bcond_default_lto}",
                "%bcond_without lto",
                "%else",
                "%bcond_with lto",
                "%endif",
            ],
            [
                True,
                False,
                True,
                True,
                True,
            ],
            lambda expr: (
                ""
                if expr == "%{bcond_default_lto}"
                else "0" if expr == "%{expr:0}" else expr
            ),
        ),
    ],
)
def test_process_conditions(lines, validity, expand_func):
    def expand(expr):
        return expand_func(expr)

    flexmock(Macros).should_receive("expand").replace_with(expand)
    processed_lines, processed_validity = zip(*process_conditions(lines))
    assert list(processed_lines) == lines
    assert list(processed_validity) == validity
    processed_lines, processed_validity = zip(
        *process_conditions(lines, MacroDefinitions.parse(lines))
    )
    assert list(processed_lines) == lines
    assert list(processed_validity) == validity
