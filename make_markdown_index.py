#!/usr/bin/python3
# -*- coding: utf-8; -*-
"""构建markdown的目录"""

import re
from sys import argv, stdin, stderr
from typing import Generator, Optional


def usage() -> str:
    return f"{argv[0]} <FILE>"

def read() -> str:
    match argv:
        case _, "-h" | "--help":
            print(usage())
            print("build markdown index")
            exit()
        case _, "-":
            return stdin.read()
        case _, name:
            with open(name, "r") as file:
                return file.read()
        case _, *args:
            print(
                    f"Input Args Invalid. ({args!r})",
                    usage(),
                    file=stderr,
                    sep="\n",
            )
            exit(2)
        case _:
            raise RuntimeError()


def generate_index(
        root: dict,
        prefix: Optional[str] = None,
        insert_prefix: str = "- ",
        ) -> Generator[str, None, None]:
    filter_list = r"""[!"#$%&'()*+,./:;<=>?@\[\\\]^`{|}~]"""
    if root:
        if prefix is None:
            prefix = insert_prefix
        for title, elems in root.items():
            linked_title = re.sub(filter_list, "", title.replace(" ", "-"))

            yield f"{prefix}[{title}](#{linked_title})"
            yield from generate_index(elems, prefix=f"{insert_prefix}{prefix}")


def build_tree(lines: list[str]) -> dict:
    prev: str = ""
    stack = [{}]

    def add(level: int, title: str):
        while len(stack) > level:
            stack.pop()
        last = stack[-1]
        new_root = {}
        last[title] = new_root
        stack.append(new_root)

    for line in lines:
        if (title := re.match(r"^\s*(#+)\s+(\S+(?:\s?\S+)*)\s*$", line)) is not None:
            add(len(title[1]), title[2])
        elif (title := re.match(r"^\s*(\S+(?:\s+\S+)*)\s*$", prev))\
                and (floor := re.match(r"^\s*(?:(={3,})|(?:-{3,}))\s*$", line)):
            add(int(floor[1] is None) + 1, title[1])
        prev = line

    return stack[0]


if __name__ == '__main__':
    text = read()
    lines = text.splitlines()
    tree = build_tree(lines)
    for line in generate_index(tree):
        print(line)
