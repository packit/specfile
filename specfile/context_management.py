# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import collections
import contextlib
import functools
import io
import os
import pickle
import sys
import tempfile
import types
from typing import Any, Callable, Dict, Generator, List, Optional, overload


@contextlib.contextmanager
def capture_stderr() -> Generator[List[bytes], None, None]:
    """
    Context manager for capturing output to _stderr_. A _stderr_ output
    of anything run in its context will be captured in the target variable
    of the __with__ statement.

    Yields:
        List of captured lines.
    """
    assert sys.__stderr__, "stderr should exist"
    fileno = sys.__stderr__.fileno()
    with tempfile.TemporaryFile() as stderr, os.fdopen(os.dup(fileno)) as backup:
        sys.stderr.flush()
        os.dup2(stderr.fileno(), fileno)
        data: List[bytes] = []
        try:
            yield data
        finally:
            sys.stderr.flush()
            os.dup2(backup.fileno(), fileno)
            stderr.flush()
            stderr.seek(0, io.SEEK_SET)
            data.extend(stderr.readlines())


class GeneratorContextManager(contextlib._GeneratorContextManager):
    """
    Extended `contextlib._GeneratorContextManager` that provides `content` property.
    """

    def __init__(self, function: Callable) -> None:
        super().__init__(function, tuple(), {})

    def __del__(self) -> None:
        # make sure the generator is fully consumed, as it is possible
        # that neither __enter__() nor content() have been called
        collections.deque(self.gen, maxlen=0)

    @property
    def content(self) -> Any:
        """
        Fully consumes the underlying generator and returns the yielded value.

        Returns:
            Value that would normally be the target variable of an associated __with__ statement.

        Raises:
            StopIteration: If the underlying generator is already exhausted.
        """
        result = next(self.gen)
        next(self.gen, None)
        return result


class ContextManager:
    """
    Class for decorating generator functions that should act as a context manager.

    Just like with `contextlib.contextmanager`, the generator returned from the decorated function
    must yield exactly one value that will be used as the target variable of the with statement.
    If the same function with the same arguments is called again from within previously generated
    context, the generator will be ignored and the target variable will be reused.

    Attributes:
        function: Decorated generator function.
        generators: Mapping of serialized function arguments to generators.
        values: Mapping of serialized function arguments to yielded values.
    """

    def __init__(self, function: Callable) -> None:
        self.function = function
        self.is_bound = False
        self.generators: Dict[bytes, Generator[Any, None, None]] = {}
        self.values: Dict[bytes, Any] = {}
        functools.update_wrapper(self, function)

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> "ContextManager":
        pass

    @overload
    def __get__(self, obj: object, objtype: Optional[type] = None) -> types.MethodType:
        pass

    # implementing __get__() makes the class a non-data descriptor,
    # so it can be used as method decorator
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        self.is_bound = True
        return types.MethodType(self, obj)

    def __call__(self, *args: Any, **kwargs: Any) -> GeneratorContextManager:
        # serialize the passed arguments
        payload = list(args) + sorted(kwargs.items())
        if payload and self.is_bound:
            # do not attempt to pickle self/cls
            payload[0] = (type(payload[0]), id(payload[0]))
        key = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
        if (
            key in self.generators
            # gi_frame is None only in case generator is exhausted
            and self.generators[key].gi_frame is not None  # type: ignore[attr-defined]
        ):
            # generator is suspended, use existing value
            def existing_value():
                try:
                    yield self.values[key]
                except KeyError:
                    # if the generator is being consumed in GeneratorContextManager destructor,
                    # self.values[key] could have already been deleted
                    pass

            return GeneratorContextManager(existing_value)
        # create the generator
        self.generators[key] = self.function(*args, **kwargs)
        # first iteration yields the value
        self.values[key] = next(self.generators[key])

        def new_value():
            try:
                yield self.values[key]
            finally:
                # second iteration wraps things up
                next(self.generators[key], None)
                # the generator is now exhausted and the value is no longer valid
                del self.generators[key]
                del self.values[key]

        return GeneratorContextManager(new_value)
