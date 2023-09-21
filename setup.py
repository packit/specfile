#!/usr/bin/python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from setuptools import setup

# we can't use pre-release-based version scheme because it generates versions
# that are sorted higher than the last stable release by RPM
# for example:
#   - pre-release (guess-next-dev):
#       0.20.1.dev1+g0abcdef.d20230921 > 0.20.1
#   - post-release (no-guess-dev):
#       0.20.0.post1.dev1+g0abcdef < 0.20.1
setup(use_scm_version={"version_scheme": "no-guess-dev"})
