# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest
from flexmock import flexmock

from specfile.value_parser import (
    BuiltinMacro,
    ConditionalMacroExpansion,
    EnclosedMacroSubstitution,
    Macros,
    MacroSubstitution,
    ShellExpansion,
    StringLiteral,
    ValueParser,
)


@pytest.mark.parametrize(
    "value, nodes",
    [
        ("", []),
        ("escaped %%macro", [StringLiteral("escaped %%macro")]),
        (
            "%(echo %{version} | cut -d. -f3)",
            [ShellExpansion("echo %{version} | cut -d. -f3")],
        ),
        ("%version", [MacroSubstitution("version")]),
        ("1%{?dist}", [StringLiteral("1"), EnclosedMacroSubstitution("?dist")]),
        ("%{longdesc %{name}}", [EnclosedMacroSubstitution("longdesc %{name}")]),
        (
            "%{fedorarel}%{?dist}.2",
            [
                EnclosedMacroSubstitution("fedorarel"),
                EnclosedMacroSubstitution("?dist"),
                StringLiteral(".2"),
            ],
        ),
        (
            "%{?prever:0.}%{mainrel}%{?prever:.%{prerpmver}}",
            [
                ConditionalMacroExpansion("?prever", [StringLiteral("0.")]),
                EnclosedMacroSubstitution("mainrel"),
                ConditionalMacroExpansion(
                    "?prever",
                    [StringLiteral("."), EnclosedMacroSubstitution("prerpmver")],
                ),
            ],
        ),
        (
            '%{lua:ver = string.gsub(rpm.expand("%{ver}"), "-", "~"); print(string.lower(ver))}',
            [
                BuiltinMacro(
                    "lua",
                    'ver = string.gsub(rpm.expand("%{ver}"), "-", "~"); print(string.lower(ver))',
                )
            ],
        ),
    ],
)
def test_parse(value, nodes):
    assert ValueParser.parse(value) == nodes


@pytest.mark.parametrize(
    "value, macros, entries, regex, template",
    [
        (
            "%(echo %version | cut -d. -f1,2).0",
            {"%(echo %version | cut -d. -f1,2)": "1.1"},
            [],
            "^1\\.1(?P<sub_0>.+?)$",
            "%(echo %version | cut -d. -f1,2)${sub_0}",
        ),
        (
            "%version",
            {"%version": "1.0"},
            ["version"],
            "^(?P<version>.+?)$",
            "%version",
        ),
        (
            "%?version",
            {"%?version": "1.0"},
            ["version"],
            "^(?P<version>.+?)$",
            "%?version",
        ),
        (
            "%!?version",
            {"%!?version": ""},
            ["version"],
            "^$",
            "%!?version",
        ),
        (
            "1%{?dist}",
            {"%{?dist}": ".fc35"},
            [],
            "^(?P<sub_0>.+?)\\.fc35$",
            "${sub_0}%{?dist}",
        ),
        (
            "%{longdesc %name}",
            {"%{longdesc %name}": "Lorem ipsum dolor sit amet"},
            ["longdesc"],
            "^Lorem\\ ipsum\\ dolor\\ sit\\ amet$",
            "%{longdesc %name}",
        ),
        (
            "%{?prever:0.}%{mainrel}%{?prever:.%{prerpmver}}",
            {
                "%?prever": "beta3",
                "%{prerpmver}": "%(echo \"%{?prever}\" | sed -e 's|-||g')",
                "%{mainrel}": "2",
            },
            ["prever", "prerpmver", "mainrel"],
            "^(?P<sub_0>.+?)\\.(?P<mainrel>.+?)\\.(?P<prerpmver>.+?)$",
            "%{?prever:${sub_0}.}%{mainrel}%{?prever:.%{prerpmver}}",
        ),
        (
            "%{mingw64_libdir}/lib%{pkgname}stub%{majorver1}%{majorver2}.a",
            {
                "%{mingw64_libdir}": "/usr/x86_64-w64-mingw32/sys-root/mingw/lib",
                "%{pkgname}": "tk",
                "%{majorver1}": "8",
                "%{majorver2}": "6",
            },
            ["pkgname", "majorver1", "majorver2"],
            "^$",
            "%{mingw64_libdir}/lib%{pkgname}stub%{majorver1}%{majorver2}.a",
        ),
    ],
)
def test_construct_regex(value, macros, entries, regex, template):
    flexmock(Macros, expand=lambda m: macros.get(m, ""))
    r, t = ValueParser.construct_regex(value, entries)
    assert r.pattern == regex
    assert t.template == template
