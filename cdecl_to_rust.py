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
测试使用的 cdecl 版本为 2.5-3
注意: 目前发现变量名 func 在 cdecl 会触发语法错误
"""

import re

from typing import Any, Callable, Generic, Self, Optional, TypeVar
from re import Pattern, findall, escape


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
        return f"{self.__class__.__name__}({self.fmtter!r}, {self.args})"


class LazyStr:
    """惰性初始化的字符串"""
    def __init__(self, data: Callable[[], str]):
        self.initer = data
        self.__inited = False
        self.__dataed: Optional[str] = None

    def __str__(self) -> str:
        """__str__"""
        if not self.__inited:
            self.__dataed = self.initer()
            self.__inited = True
        return self.__dataed  # type: ignore

    def __repr__(self) -> str:
        """__repr__"""
        if self.__inited:
            value = f"inited: {self.__dataed!r}"
        else:
            value = f"noinit: {self.initer!r}"
        return f"{self.__class__.__name__}({value})"


EMPTYS = r" \t\r\n"
LONG_SPLITS = ["->"]  # 单独成一个token的字符串, 必须完全由单分隔字符组成
LONG_SPLITS.sort(key=len, reverse=True)  # 长度必须为递减
LONG_SPLIT_INLINE_REGEX = "|".join(map(escape, LONG_SPLITS))
LONG_SPLIT_REGEX = fr"(?:{LONG_SPLIT_INLINE_REGEX})"
SPLIT_CHARS = escape(r""""#$%&'()*+,-./:;<=>?@[\]^`{|}~""")
IDENT_PAT = f"[^{EMPTYS}{SPLIT_CHARS}]+"
# 根据 findall 返回 [(str, str)] 仅取元素 1 以跳过空匹配
SPLIT_FIND_REGEX = (
        fr"([{EMPTYS}]+)|({LONG_SPLIT_REGEX}"
        fr"|[{SPLIT_CHARS}]|{IDENT_PAT})")
SPLIT_FIND_REGEX_OBJ: Pattern[str] = re.compile(SPLIT_FIND_REGEX)


def split_tokens(source: str) -> list[str]:
    """简单的通用词法分割 (基于单长分割字符与单长空白字符)
    """
    find_res = SPLIT_FIND_REGEX_OBJ.findall(source)
    return [i[1] for i in find_res if i[1]]


def assert_eq(val1: Any, val2: Any) -> None:
    """assert_eq
    """
    if not val1 == val2:
        raise AssertionError(val1, val2)


def dbg(target):
    """function decortor, target: function"""
    def inner(*args, **kwargs):
        print(args, kwargs)
        result = target(*args, **kwargs)
        print(repr(result))
        return result
    return inner


T = TypeVar("T")
class Tokens(Generic[T]):
    """用于遍历及预查的类
    """
    def __init__(self, data: list[T] | tuple[T]):
        self.data: list[T] | tuple[T] = data
        self.idx: int = 0

    def get(self) -> T:
        """get next value and index next
        """
        res = self.data[self.idx]
        self.idx += 1
        return res

    def get_next(self, step: int = 0) -> Optional[T]:
        """get_next
        """
        try:
            return self.data[self.idx + step]
        except IndexError:
            return None

    def check_to_end(self, raise_fun: Callable[[], BaseException]) -> None:
        """check
        """
        if self.idx != len(self.data):
            raise raise_fun()


def english_to_rs(input_tokens: list[str]) -> str:
    """english_to_rs
    input:
    `declare <name> as <english>` or `cast <name> into <english>`
    """
    length = len(input_tokens)
    if length < 4:
        raise ValueError(f"length < 4, {input_tokens}")

    tokens = Tokens(input_tokens)

    def get() -> str:
        return tokens.get()

    def build() -> FmtNode:
        match get():
            case "function":
                assert_eq(get(), "(")
                params: list[FmtNode] = []
                while tokens.get_next() != ")":
                    params.append(build())
                    if tokens.get_next() == ",":
                        assert_eq(get(), ",")
                assert_eq(get(), ")")
                assert_eq(get(), "returning")
                result = FmtNode(
                        "fn({}) -> {}",
                        LazyStr(lambda: ", ".join(map(str, params))),
                        build())
            case "pointer":
                assert_eq(get(), "to")
                result = FmtNode("*{}", build())
            case "array":
                num_text = get()
                if num_text == "of":
                    # non size array
                    return FmtNode("[{}]", build())
                num: int = int(num_text)
                assert_eq(get(), "of")
                result = FmtNode("[{}; {}]", build(), num)
            case ("struct" | "union" | "enum"
                  | "const" | "volatile" | "noalias"
                  | "signed" | "unsigned" | "register"
                  | "static") as type_:
                # 带括号的结构
                result = FmtNode(f"{type_}({{}})", build())
            case ("long" | "short") as type_:
                # 整数修饰类
                count = 1
                while True:
                    next_ = tokens.get_next()
                    if next_ == type_:
                        count += 1
                        get()
                        continue
                    if next_ == "int":
                        get()
                        return FmtNode(f"{' '.join((type_,) * count)} int")
                    result = FmtNode(f"{' '.join((type_,) * count)}")
            case token:
                result = FmtNode("{}", token)
        return result

    def check_builded(root: FmtNode) -> None:
        tokens.check_to_end(lambda: AssertionError(
            f"Not fully build: ({root}): {' '.join(tokens.data)!r}"))

    match get():
        case "declare":
            var_name: str = get()
            assert_eq(get(), "as")
            root: FmtNode = FmtNode("{}: {}", var_name, build())
        case "cast":
            var_name: str = get()
            assert_eq(get(), "into")
            root: FmtNode = FmtNode("{} as {}", var_name, build())
        case head:
            raise AssertionError(
                    f"{head!r} no pattern, ({' '.join(input_tokens)})")

    check_builded(root)
    return str(root)


def rs_to_english(input_tokens: list[str]) -> str:
    """rs to english
    """
    length = len(input_tokens)
    if length < 3:
        raise ValueError(f"length < 3, {input_tokens}")
    tokens = Tokens(input_tokens)

    def check_builded(root: FmtNode) -> None:
        tokens.check_to_end(lambda: AssertionError(
            f"Not fully build: ({root}): {' '.join(tokens.data)!r}"))

    def get() -> str:
        return tokens.get()

    def build() -> FmtNode:
        """通用构建树"""
        match get():
            case "[":
                # array
                type_ = build()
                match get():
                    case ";":
                        # sized array
                        num = int(get())
                        assert_eq(get(), "]")
                        result = FmtNode("array {} of {}", num, type_)
                    case "]":
                        # non size array
                        result = FmtNode("array of {}", type_)
                    case end:
                        raise AssertionError(
                                "array format error, need ';' or ']', "
                                f"found {end!r}")
            case "*":
                result = FmtNode("pointer to {}", build())
            case "fn":
                assert_eq(get(), "(")
                params: list[FmtNode] = []
                while tokens.get_next() != ")":
                    # 循环代表未结束 (type[,])
                    params.append(build())
                    if tokens.get_next() == ",":
                        # 消耗时顺便断言检测下是否内部出错
                        assert_eq(tokens.get(), ",")
                assert_eq(get(), ")")
                assert_eq(get(), "->")
                result = FmtNode(
                        "function ({}) returning {}",
                        LazyStr(lambda: ", ".join(map(str, params))),
                        build())
            case ("struct" | "union" | "enum" | "const"
                  | "volatile" | "noalias" | "signed" | "unsigned"
                  | "register" | "static") as type_:
                assert_eq(get(), "(")
                value = build()
                assert_eq(get(), ")")
                result = FmtNode(f"{type_} {{}}", value)
            case ("long" | "short") as type_:
                # 多个长或短前缀整数
                count = 1
                while True:
                    next_ = tokens.get_next()
                    if next_ == type_:
                        # continue
                        count += 1
                        get()
                        continue
                    if next_ == "int":
                        # end int
                        get()
                        return FmtNode(f"{' '.join((type_,) * count)} int")
                    result = FmtNode(f"{' '.join((type_,) * count)}")
                    break  # no end int
            case value:
                result = FmtNode("{}", value)
        return result

    var_name = get()

    match get():
        case ":":
            # define
            root = FmtNode("declare {} as {}", var_name, build())
        case "as":
            # type into
            root = FmtNode("cast {} into {}", var_name, build())
        case head:
            raise AssertionError(
                    f"{head!r} no pattern, ({' '.join(input_tokens)})")

    check_builded(root)
    return str(root)


def test() -> None:
    """test function"""
    # lazy import
    import sys  # pylint: disable=import-outside-toplevel
    from os import popen  # pylint: disable=import-outside-toplevel

    cdecl_bin = r"/bin/cdecl"

    result = english_to_rs(split_tokens(" ".join(sys.argv[1:])))
    print(result)
    cdecl_text = rs_to_english(split_tokens(result))
    print(cdecl_text)
    with popen(cdecl_bin, mode="w") as proc:
        print(cdecl_text, file=proc, flush=True)


if __name__ == '__main__':
    test()
