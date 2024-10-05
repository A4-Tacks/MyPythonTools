#!/usr/bin/python3
# -*- coding: utf-8; -*-
"""简单实现一个基础的词法高亮
随便写的, 类型检查都没开就别管那么多了
"""

from regex import match


class ColorStr:
    def __init__(self):
        self.s = ""
        self.colors = [0]

    def enter(self, color: int) -> None:
        self.colors.append(color)
        if color >= 0:
            self.s += f"\x1b[{color}m"

    def exit(self) -> int:
        poped = self.colors.pop()
        for i in range(len(self.colors)-1, -1, -1):
            if self.colors[i] >= 0:
                color = self.colors
        self.s += f"\x1b[{self.colors[-1]}m"
        return poped

    def add(self, s: str):
        self.s += s

    def word(self, color: int, s: str):
        self.enter(color)
        self.add(s)
        self.exit()


class Pat:
    color = -1

    def run(self, s: str, ctx: "Ctx") -> bool | None: ...


class MatchPat(Pat):
    def __init__(self, pat, color=-1):
        self.pat = pat
        self.color = color

    def run(self, s, ctx: "Ctx"):
        if res := match(self.pat, s):
            ctx.word_to(self.color, res.span()[1])
            return True

    def __repr__(self):
        return f"MatchPat({self.pat!r}, {self.color})"


class RegionPat(Pat):
    def __init__(self, start, end, color=-1, contains=None):
        self.start = start
        self.end = end
        self.color = color
        self.contains = contains or []

    def run(self, s, ctx: "Ctx"):
        if res := match(self.start, s):
            ctx.envs.append(Env(self.contains, color=self.color, end=self.end))
            ctx.out.enter(self.color)

            ctx.word_to(self.color, res.span()[1])
            return True

    def __repr__(self):
        return f"RegionPat({self.start!r}, {self.end!r}, " \
                f"+{len(self.contains)})"


class Env:
    def __init__(self, pats: list[Pat], color=-1, end=None):
        self.end = end
        self.pats = pats
        self.color = color

    def __repr__(self):
        return f"Env({self.pats}, end={self.end})"


class Ctx:
    def __init__(self, s, pats: list[Pat]):
        self.s = s
        self.out = ColorStr()
        self.envs = [Env(pats, color=0)]


    def next_to(self, i: int) -> None:
        self.s = self.s[i:]


    def word_to(self, color: int, i: int) -> None:
        self.out.word(color, self.s[:i])
        self.next_to(i)


    def do(self) -> bool:
        for pat in self.envs[-1].pats:
            if pat.run(self.s, self):
                return True

        if (end := self.envs[-1].end) and end is not None \
                and (res := match(end, self.s)):
            last = self.envs.pop()
            self.out.exit()
            self.word_to(last.color, res.span()[1])
            return True

        self.out.add(self.s[:1])
        self.s = self.s[1:]
        return bool(self.s)


def mini_test():
    src = r'"abc\ndef" to "abcdef" to "abc\"d\\e\\\\f\\\g" end' "\n"\
            r'(0) 0 (0(0)0)0 {0}0 {0{0}0}0 {0(0)0}0 {0(0(0)0)0}0' "\n"\
            r'{"nohi"0("hi"0{"nohi"0}"hi"0)"nohi"0}0' "\n"

    paren_pat = RegionPat(r'\(', r'\)', color=33)
    brace_pat = RegionPat(r'\{', r'\}', color=94)
    str_pat = RegionPat('"', '"', color=31, contains=[
            MatchPat(r'\\.', 32)])

    brace_pat.contains.extend([brace_pat, paren_pat]) # 交叉递归匹配
    paren_pat.contains.extend([brace_pat, paren_pat, str_pat]) # 交叉递归匹配

    # 在顶层高亮字符串和花括号
    # 在花括号内可以存在圆括号和花括号
    # 在圆括号内可以存在字符串圆括号和花括号
    pats = [
            str_pat,
            brace_pat]

    print(f"{pats=}")
    print(f"{str_pat=}")
    print(f"{brace_pat=}")
    print(f"{paren_pat=}")

    ctx = Ctx(src, pats)
    while ctx.do(): pass
    print(ctx.s, "\x1b[0m")
    print(ctx.out.s, "\x1b[0m")
    print(f"{ctx.envs=}")
    print("--envs")

    for env in ctx.envs:
        print("  env_pats:", env.pats)


if __name__ == '__main__':
    mini_test()
