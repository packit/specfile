# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import contextlib
from collections.abc import Iterator
from typing import Callable, Generator, ParamSpec, TypeVar

_T_co = TypeVar("_T_co", covariant=True)
_P = ParamSpec("_P")

@contextlib.contextmanager
def capture_stderr() -> Generator[list[bytes], None, None]: ...

class GeneratorContextManager(contextlib._GeneratorContextManager[_T_co]):
    def __init__(self, function: Callable[..., _T_co]) -> None: ...
    def __del__(self) -> None: ...
    @property
    def content(self) -> _T_co: ...

# Instead of the original descriptor class, tell the type checker to treat
# ContextManager as a simple decorator function which is something that it
# understands.
def ContextManager(
    func: Callable[_P, Iterator[_T_co]],
) -> Callable[_P, GeneratorContextManager[_T_co]]: ...
