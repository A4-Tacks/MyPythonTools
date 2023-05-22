#!/usr/bin/python3
# -*- coding: utf-8; -*-
"""test file"""

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
