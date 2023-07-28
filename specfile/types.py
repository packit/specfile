# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import abc

from typing_extensions import Protocol


# define our own SupportsIndex type for older version of typing_extensions (EL 8)
class SupportsIndex(Protocol, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __index__(self) -> int:
        ...
