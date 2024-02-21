#!/usr/bin/python

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import subprocess
from pathlib import Path

import fmf

# Set discover of specfile tests to a fixed commit
tree_root = Path.cwd().absolute()
tree = fmf.Tree(tree_root)
main_node = tree.find("/plans")
with main_node as data:
    data["discover"]["url"] = "https://github.com/packit/specfile.git"
    data["discover"]["ref"] = (
        subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    )


# Set discover of packit integration tests to the current main
packit_node = tree.find("/plans/packit-integration")
with packit_node as data:
    data["discover"]["ref"] = (
        subprocess.check_output(
            ["git", "ls-remote", "https://github.com/packit/packit", "main"]
        )
        .decode()
        .strip()
        .split()[0]
    )
