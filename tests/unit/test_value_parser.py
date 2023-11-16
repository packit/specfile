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
    "value, macros, modifiable_entities, flippable_entities, regex, template, entities_to_flip",
    [
        (
            "%(echo %version | cut -d. -f1,2).0",
            {"%(echo %version | cut -d. -f1,2)": "1.1"},
            set(),
            set(),
            "^1\\.1(?P<sub_0>.+?)$",
            "%(echo %version | cut -d. -f1,2)${sub_0}",
            set(),
        ),
        (
            "%version",
            {"%version": "1.0"},
            {"version"},
            set(),
            "^(?P<version>.+)$",
            "%version",
            set(),
        ),
        (
            "%?version",
            {"%?version": "1.0"},
            {"version"},
            set(),
            "^(?P<version>.+)$",
            "%?version",
            set(),
        ),
        (
            "%!?version",
            {"%!?version": ""},
            {"version"},
            set(),
            "^$",
            "%!?version",
            set(),
        ),
        (
            "1%{?dist}",
            {"%{?dist}": ".fc35"},
            set(),
            set(),
            "^(?P<sub_0>.+?)\\.fc35$",
            "${sub_0}%{?dist}",
            set(),
        ),
        (
            "%{longdesc %name}",
            {"%{longdesc %name}": "Lorem ipsum dolor sit amet"},
            {"longdesc"},
            set(),
            "^Lorem\\ ipsum\\ dolor\\ sit\\ amet$",
            "%{longdesc %name}",
            set(),
        ),
        (
            "%{?prever:0.}%{mainrel}%{?prever:.%{prerpmver}}",
            {
                "%{?prever:1}": "1",
                "%{prerpmver}": "%(echo \"%{?prever}\" | sed -e 's|-||g')",
                "%{mainrel}": "2",
            },
            {"prever", "prerpmver", "mainrel"},
            {"prever", "prerpmver", "mainrel"},
            "^(?P<sub_0>.+?)\\.(?P<mainrel>.+)\\.(?P<prerpmver>.+)$",
            "%{?prever:${sub_0}.}%{mainrel}%{?prever:.%{prerpmver}}",
            set(),
        ),
        (
            "%{?prever:0.}%{mainrel}%{?prever:.%{prerpmver}}",
            {
                "%{prerpmver}": "%(echo \"%{?prever}\" | sed -e 's|-||g')",
                "%{mainrel}": "2",
            },
            {"prever", "prerpmver", "mainrel"},
            {"prever", "prerpmver", "mainrel"},
            "^(?P<sub_0>.+?)\\.(?P<mainrel>.+)\\.(?P<prerpmver>.+)$",
            "%{?prever:${sub_0}.}%{mainrel}%{?prever:.%{prerpmver}}",
            {"prever"},
        ),
        (
            "%{mingw64_libdir}/lib%{pkgname}stub%{majorver1}%{majorver2}.a",
            {
                "%{mingw64_libdir}": "/usr/x86_64-w64-mingw32/sys-root/mingw/lib",
                "%{pkgname}": "tk",
                "%{majorver1}": "8",
                "%{majorver2}": "6",
            },
            {"pkgname", "majorver1", "majorver2"},
            {"pkgname", "majorver1", "majorver2"},
            "^$",
            "%{mingw64_libdir}/lib%{pkgname}stub%{majorver1}%{majorver2}.a",
            set(),
        ),
        (
            "%{?commit:%{commit}}%{?!commit:%{tag}}",
            {"%{?commit:1}": "1"},
            {"commit", "tag"},
            {"commit", "tag"},
            "^(?P<commit>.+)$",
            "%{?commit:%{commit}}%{?!commit:%{tag}}",
            set(),
        ),
        (
            "%{?commit:%{commit}}%{?!commit:%{tag}}",
            {},
            {"commit", "tag"},
            {"commit", "tag"},
            "^(?P<commit>.+)$",
            "%{?commit:%{commit}}%{?!commit:%{tag}}",
            {"commit"},
        ),
    ],
)
def test_construct_regex(
    value,
    macros,
    modifiable_entities,
    flippable_entities,
    regex,
    template,
    entities_to_flip,
):
    flexmock(Macros, expand=lambda m: macros.get(m, ""))
    r, t, etf = ValueParser.construct_regex(
        value, modifiable_entities, flippable_entities
    )
    assert r.pattern == regex
    assert t.template == template
    assert etf == entities_to_flip
