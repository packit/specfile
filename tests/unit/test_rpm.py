# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from pathlib import Path

import rpm

from specfile.rpm import RPM, Macro, MacroLevel, Macros


def test_macros_parse():
    assert Macros._parse(
        [
            "-20= dump\t<builtin>\n",
            "-20: echo\t<builtin>\n",
            "-13: fontrpmname\t%{lua:\n",
            'local fonts = require "fedora.srpm.fonts"\n',
            'print(fonts.rpmname(rpm.expand("%1")))\n',
            "}\n",
            "-13: __scm_apply_git(qp:m:)\t\n",
            "%{__git} apply --index --reject %{-p:-p%{-p*}} -\n",
            '%{__git} commit %{-q} -m %{-m*} --author "%{__scm_author}"\n',
            "-13: py3_build_wheel\t%{expand:\\\n",
            '  CFLAGS="${CFLAGS:-${RPM_OPT_FLAGS}}" LDFLAGS="${LDFLAGS:-${RPM_LD_FLAGS}}"\\\n',
            "  %{__python3} %{py_setup} %{?py_setup_args} bdist_wheel %{?*}\n",
            "}\n",
            " -1: _sourcedir\t.\n",
            "========================\n",
        ]
    ) == [
        Macro("dump", None, "<builtin>", -20, True),
        Macro("echo", None, "<builtin>", -20, False),
        Macro(
            "fontrpmname",
            None,
            (
                "%{lua:\n"
                'local fonts = require "fedora.srpm.fonts"\n'
                'print(fonts.rpmname(rpm.expand("%1")))\n'
                "}"
            ),
            -13,
            False,
        ),
        Macro(
            "__scm_apply_git",
            "(qp:m:)",
            (
                "%{__git} apply --index --reject %{-p:-p%{-p*}} -\n"
                '%{__git} commit %{-q} -m %{-m*} --author "%{__scm_author}"'
            ),
            -13,
            False,
        ),
        Macro(
            "py3_build_wheel",
            None,
            (
                "%{expand:"
                '  CFLAGS="${CFLAGS:-${RPM_OPT_FLAGS}}" LDFLAGS="${LDFLAGS:-${RPM_LD_FLAGS}}"'
                "  %{__python3} %{py_setup} %{?py_setup_args} bdist_wheel %{?*}\n"
                "}"
            ),
            -13,
            False,
        ),
        Macro("_sourcedir", None, ".", -1, False),
    ]


def test_macros_remove():
    rpm.reloadConfig()
    macros = Macros.dump()
    rpm.addMacro("test", "1")
    rpm.addMacro("test", "2")
    rpm.addMacro("test", "3")
    assert set(Macros.dump()).difference(macros) == {
        Macro("test", None, "3", -1, False)
    }
    Macros.remove("test")
    Macros.remove("non_existent_macro")
    assert Macros.dump() == macros


def test_macros_define():
    rpm.reloadConfig()
    macros = Macros.dump()
    Macros.define("test", "1")
    # redefine builtin macro
    Macros.define("echo", "2")
    assert set(Macros.dump()).difference(macros) == {
        Macro("test", None, "1", -1, False),
        Macro("echo", None, "2", -1, False),
    }


def test_macros_reinit():
    Macros.reinit(MacroLevel.BUILTIN)
    assert all(m.level == MacroLevel.BUILTIN for m in Macros.dump())


def test_rpm_parse():
    spec = RPM.parse(
        (
            "Name:           test\n"
            "Version:        0.1\n"
            "Release:        1%{?dist}\n"
            "Summary:        Test package\n"
            "License:        MIT\n"
            "\n"
            "%description\n"
            "Test package\n"
        ),
        Path("."),
        macros=[("dist", ".fc35")],
    )
    assert spec.sourceHeader[rpm.RPMTAG_NAME] == "test"
    assert spec.sourceHeader[rpm.RPMTAG_VERSION] == "0.1"
    assert spec.sourceHeader[rpm.RPMTAG_RELEASE] == "1.fc35"
    assert spec.sourceHeader[rpm.RPMTAG_SUMMARY] == "Test package"
    assert spec.sourceHeader[rpm.RPMTAG_LICENSE] == "MIT"
    assert spec.prep is None
