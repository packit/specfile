# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import abc

try:
    from typing import SupportsIndex
except ImportError:
    # define our own SupportsIndex type for older version of typing (Python 3.7 and older)
    from typing_extensions import Protocol

    class SupportsIndex(Protocol, metaclass=abc.ABCMeta):  # type: ignore [no-redef]
        @abc.abstractmethod
        def __index__(self) -> int: ...
