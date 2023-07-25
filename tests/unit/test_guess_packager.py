# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import subprocess
from pathlib import Path

import pytest

# old pytest versions don't expose MonkeyPatch
from _pytest.monkeypatch import MonkeyPatch
from flexmock import flexmock

import specfile.changelog
from specfile.changelog import guess_packager
from specfile.macros import Macros


@pytest.fixture
def clean_guess_packager(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """
    Ensure a clean environment
    """
    # For $RPM_PACKAGER
    monkeypatch.delenv("RPM_PACKAGER", False)
    # Make sure git doesn't read existing config
    monkeypatch.setenv("HOME", "/dev/null")
    monkeypatch.delenv("XDG_CONFIG_HOME", False)
    monkeypatch.chdir(tmp_path)
    # For %packager
    Macros.remove("packager")
    # For Unix passwd guessing
    flexmock(specfile.changelog).should_receive("_getent_name").and_return("")


@pytest.fixture
def set_packager_env(monkeypatch: MonkeyPatch) -> str:
    packager = "Patty Packager <patty@packager.me>"
    monkeypatch.setenv("RPM_PACKAGER", packager)
    return packager


@pytest.fixture
def set_packager_git(monkeypatch: MonkeyPatch, tmp_path: Path) -> str:
    packager = "Packager, Patty <packager@patty.dev>"

    monkeypatch.chdir(tmp_path)
    subprocess.run(
        ["git", "init", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    subprocess.run(
        ["git", "config", "user.name", "Packager, Patty"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "config", "user.email", "packager@patty.dev"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return packager


@pytest.fixture
def set_packager_macro() -> str:
    packager = "Patricia Packager"
    Macros.define("packager", packager)
    return packager


@pytest.fixture
def set_packager_passwd() -> str:
    packager = "Ms. Packager"
    flexmock(specfile.changelog).should_receive("_getent_name").and_return(packager)
    return packager


def test_guess_packager_env(clean_guess_packager, set_packager_env):
    assert guess_packager() == set_packager_env


def test_guess_packager_macro(clean_guess_packager, set_packager_macro):
    assert guess_packager() == set_packager_macro


def test_guess_packager_git(clean_guess_packager, set_packager_git):
    assert guess_packager() == set_packager_git


def test_guess_packager_passwd(clean_guess_packager, set_packager_passwd):
    assert guess_packager() == set_packager_passwd


def test_guess_packager_pref1(
    clean_guess_packager,
    set_packager_env,
    set_packager_macro,
    set_packager_git,
    set_packager_passwd,
):
    assert guess_packager() == set_packager_env


def test_guess_packager_pref2(
    clean_guess_packager, set_packager_macro, set_packager_git, set_packager_passwd
):
    assert guess_packager() == set_packager_macro


def test_guess_packager_pref3(
    clean_guess_packager, set_packager_git, set_packager_passwd
):
    assert guess_packager() == set_packager_git


def test_guess_packager_pref4(
    clean_guess_packager, set_packager_git, set_packager_passwd
):
    subprocess.run(["git", "config", "--unset", "user.email"])
    assert guess_packager() == "Packager, Patty"


def test_guess_packager_empty(clean_guess_packager):
    """
    The function should return an empty string if it can't detect the packager
    """
    assert guess_packager() == ""
