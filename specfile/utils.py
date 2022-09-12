# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import urllib.parse
from pathlib import Path


def get_filename_from_location(location: str) -> str:
    """
    Extracts filename from given source location.

    Follows RPM logic - target filename can be specified in URL fragment.

    Args:
        location: Location to extract filename from.

    Returns:
        Extracted filename that can be empty if there is none.
    """
    url = urllib.parse.urlsplit(location)
    if url.fragment:
        if "/" in url.fragment:
            return Path(url.fragment).name.split("=")[-1]
        return Path(f"{url.path}#{url.fragment}").name
    return Path(url.path).name
