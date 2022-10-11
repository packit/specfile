# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
A library for parsing and manipulating RPM spec files
"""

from importlib.metadata import PackageNotFoundError, distribution

from specfile.specfile import Specfile

try:
    __version__ = distribution(__name__).version
except PackageNotFoundError:
    # package is not installed
    pass

__all__ = [
    Specfile.__name__,
]
