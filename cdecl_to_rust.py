#!/usr/bin/python3
# -*- coding: utf-8; -*-
"""将 rust 风格类型声明 和 cdecl 的 c语言模式描述句互相转换
仅包含指针、数组、函数指针 及其它
例如 `void(*bsd_signal(int, void(*)(int)))(int)` 会被 cdecl 转换为以下句段: 
```
declare bsd_signal as function (int, pointer to function (int)
returning void) returning pointer to function (int) returning void
```
然后会被本程序转换为:
```
bsd_signal: fn(int, *fn(int) -> void) -> *fn(int) -> void
```
"""

from typing import Any, Self, Optional
from itertools import chain


EMPTYS = set(" \t\r\n")
SPLITS = set(chain(r""""#$%&'()*+,-./:;<=>?@[\]^`{|}~""", EMPTYS))


class FmtNode:
    """格式化树, 格式化一整个树形结构"""
    @classmethod
    def new(cls, *args, **kw) -> Self:
        """use init
        """
        return cls(*args, **kw)

    def __init__(self, fmtter: str, *args: Any):
        self.fmtter = fmtter
        self.args = args

    def __str__(self) -> str:
        """__str__
        """
        return self.fmtter.format(*self.args)

    def __repr__(self) -> str:
        """__repr__
        """
        return f"{self.__class__.__name__}({repr(self.fmtter)}, {self.args})"


def assert_eq(val1: Any, val2: Any) -> None:
    """assert_eq
    """
    if not val1 == val2:
        raise AssertionError(val1, val2)


def split_tokens(source: str) -> list[str]:
    """简单的通用词法分割 (基于单长分割字符与单长空白字符)
    """
    chars = iter(source)
    tokens: list[list[str]] = [[]]
    last = tokens[-1]
    for char in chars:
        if char in EMPTYS:
            if last:
                last = []
                tokens.append(last)
        elif char in SPLITS:
            if last:
                last = []
                tokens.append(last)
            last.append(char)
            last = []
            tokens.append(last)
        else:
            last.append(char)
    return ["".join(i) for i in tokens]


def dbg(target):
    """function decortor, target: function"""
    def inner(*args, **kwargs):
        print(args, kwargs)
        result = target(*args, **kwargs)
        print(repr(result))
        return result
    return inner


def english_to_rs(tokens: list[str]) -> str:
    """english_to_rs
    input: declare <name> as <english>
    """
    length = len(tokens)
    if length < 4:
        raise ValueError(f"length < 4, {tokens}")
    idx = [0]

    def get() -> str:
        res = tokens[idx[0]]
        idx[0] += 1
        return res

    def get_next(step: int = 1) -> Optional[str]:
        if idx[0] + step < length:
            return tokens[idx[0]]
        return None

    def build() -> FmtNode:
        match get():
            case "function":
                assert_eq(get(), "(")
                params = []
                while get_next() != ")":
                    params.append(build())
                    if get_next() == ",":
                        assert_eq(get(), ",")
                assert_eq(get(), ")")
                assert_eq(get(), "returning")
                return FmtNode("fn({}) -> {}", ", ".join(map(str, params)), build())
            case "pointer":
                assert_eq(get(), "to")
                return FmtNode("*{}", build())
            case "array":
                num_text = get()
                if num_text == "of":
                    # non size array
                    return FmtNode("[{}]", build())
                num = int(num_text)
                assert_eq(get(), "of")
                return FmtNode("[{}; {}]", build(), num)
            case "struct" | "union" | "enum" as type_:
                return FmtNode(f"{type_} {{}}", build())
            case token:
                return FmtNode("{}", token)

    match get():
        case "declare":
            var_name: str = get()
            assert_eq(get(), "as")
            root: FmtNode = FmtNode("{}: {}", var_name, build())
            if not idx[0] == length:
                raise AssertionError(
                        f"Not fully build: ({root}): {repr(' '.join(tokens))}")
            return str(root)
        case "cast":
            var_name: str = get()
            assert_eq(get(), "into")
            root: FmtNode = FmtNode("{} as {}", var_name, build())
            if not idx[0] == length:
                raise AssertionError(
                        f"Not fully build: ({root}): {repr(' '.join(tokens))}")
            return str(root)
        case head:
            raise AssertionError(f"{head} no pattern")


if __name__ == '__main__':
    import sys

    print(english_to_rs(split_tokens(" ".join(sys.argv[1:]))))
