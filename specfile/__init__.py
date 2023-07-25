# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
A library for parsing and manipulating RPM spec files
"""

from specfile.specfile import Specfile

try:
    from importlib.metadata import PackageNotFoundError, distribution
except ImportError:
    from importlib_metadata import PackageNotFoundError  # type: ignore[no-redef]
    from importlib_metadata import distribution  # type: ignore[no-redef]

try:
    __version__ = distribution(__name__).version
except PackageNotFoundError:
    # package is not installed
    pass

__all__ = [
    Specfile.__name__,
]
