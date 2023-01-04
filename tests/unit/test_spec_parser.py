# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
from pathlib import Path

import rpm

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
