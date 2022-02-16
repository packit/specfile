# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
A library for parsing and manipulating RPM spec files
"""

try:
    from importlib.metadata import PackageNotFoundError, distribution
except ImportError:
    from importlib_metadata import PackageNotFoundError  # type: ignore
    from importlib_metadata import distribution  # type: ignore

try:
    __version__ = distribution(__name__).version
except PackageNotFoundError:
    # package is not installed
    pass


__all__ = [
    "specfile",
]
