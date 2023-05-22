#!/usr/bin/python3
# -*- coding: utf-8; -*-
"""a generator to wither tools lib"""

from typing import Generator, TypeAlias, Any, Callable
from types import TracebackType

WithGenerator: TypeAlias = Generator[
        Any, tuple[BaseException, tuple[Any] | Any, TracebackType], bool]
BuilderWithGenerator: TypeAlias = Callable[..., WithGenerator]


class GeneratorNoReturnError(Exception):
    """generator no return value error
    """


class Wither:
    """input generator, to with
    # Examples
    ```python
    from generator_to_with import Wither, WithGenerator

    def gen(num: int) -> WithGenerator:
        err, _err_val, _err_traceback = yield num
        if err is ZeroDivisionError:
            return True
        return False


    if __name__ == '__main__':
        n: int | None = None
        with Wither(gen(0)) as num:
            n = 10 // num
        assert n is None
        with Wither(gen(5)) as num:
            n = 10 // num
        assert n == 2
    ```

    ---
    If you don't have it, you will need to write the following code
    ```python
    class Foo:
        def __init__(self, num: int):
            self.num = num

        def __enter__(self) -> int:
            return self.num

        def __exit__(self, err, _err_val, _err_traceback) -> bool:
            if err is ZeroDivisionError:
                return True
            return False


    if __name__ == '__main__':
        n: int | None = None
        with Foo(0) as num:
            n = 10 // num
        assert n is None
        with Foo(5) as num:
            n = 10 // num
        assert n == 2
    ```
    """
    def __init__(
            self,
            generator: WithGenerator):
        self.gen: WithGenerator = generator

    def __enter__(self) -> Any:
        """__enter__
        """
        return next(self.gen)

    def __exit__(
            self,
            err: BaseException,
            err_val: tuple[Any] | Any,
            err_traceback: TracebackType) -> bool:
        """__exit__
        """
        try:
            self.gen.send((err, err_val, err_traceback))
        except StopIteration as result:
            return result.value
        raise GeneratorNoReturnError("yield no return value")
