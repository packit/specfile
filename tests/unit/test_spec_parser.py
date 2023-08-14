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


def test_spec_parser_make_dummy_sources(tmp_path):
    regular_source = "regular-source.zip"
    non_empty_source = "non-empty-source.tar.xz"
    existing_source = "existing-source.tar.gz"
    sourcedir = tmp_path / "sources"
    sourcedir.mkdir()
    (sourcedir / existing_source).write_text("...")
    parser = SpecParser(sourcedir)
    with parser._make_dummy_sources(
        {regular_source, existing_source}, {non_empty_source}
    ) as dummy_sources:
        assert all(s.exists() for s in dummy_sources)
        assert sourcedir / regular_source in dummy_sources
        assert sourcedir / non_empty_source in dummy_sources
        assert sourcedir / existing_source not in dummy_sources
    assert all(not s.exists() for s in dummy_sources)
    assert (sourcedir / existing_source).exists()
    flexmock(Path).should_receive("write_bytes").and_raise(FileNotFoundError)
    flexmock(Path).should_receive("write_text").and_raise(PermissionError)
    with parser._make_dummy_sources(
        {regular_source, existing_source}, {non_empty_source}
    ) as dummy_sources:
        assert not dummy_sources
    assert (sourcedir / existing_source).exists()
