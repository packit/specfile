# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
from pathlib import Path

import rpm
from flexmock import flexmock

from specfile.spec_parser import SpecParser


def test_spec_parser_do_parse():
    parser = SpecParser(Path("."), [("dist", ".fc35")])
    spec, _ = parser._do_parse(
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
    )
    assert spec.sourceHeader[rpm.RPMTAG_NAME] == "test"
    assert spec.sourceHeader[rpm.RPMTAG_VERSION] == "0.1"
    assert spec.sourceHeader[rpm.RPMTAG_RELEASE] == "1.fc35"
    assert spec.sourceHeader[rpm.RPMTAG_SUMMARY] == "Test package"
    assert spec.sourceHeader[rpm.RPMTAG_LICENSE] == "MIT"
    assert spec.prep is None


def test_copy_spec_parser():
    parser = SpecParser(Path("."), [("dist", ".fc35")])
    shallow_copy = copy.copy(parser)
    assert shallow_copy == parser
    assert shallow_copy is not parser
    deep_copy = copy.deepcopy(parser)
    assert deep_copy == parser
    assert deep_copy is not parser


def test_spec_parser_macros():
    flexmock(rpm).should_call("delMacro").with_args(
        "fedora"
    ).at_least().once().ordered()
    flexmock(rpm).should_call("delMacro").with_args("rhel").at_least().once().ordered()
    flexmock(rpm).should_call("addMacro").with_args("rhel", "9").once().ordered()
    # we don't care about the rest
    flexmock(rpm).should_call("addMacro")
    flexmock(rpm).should_call("delMacro")
    parser = SpecParser(Path("."), macros=[("fedora", None), ("rhel", "9")])
    spec, _ = parser._do_parse(
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
    )
