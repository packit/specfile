# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
A library for parsing and manipulating RPM spec files
"""

from pkg_resources import get_distribution, DistributionNotFound


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


__all__ = [
    "specfile",
]
