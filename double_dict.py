#!/usr/bin/python3
# -*- coding: utf-8; -*-
"""双向映射字典"""

from typing import Generic, TypeVar
from collections.abc import Iterable, Iterator, MappingView, MutableMapping, Hashable

KT = TypeVar('KT', bound=Hashable)
VT = TypeVar('VT', bound=Hashable)

class DoubleDict(Generic[KT, VT], MutableMapping[KT, VT], MappingView):
    """
    >>> d = DoubleDict([(1, 2), (2, 3)])
    >>> d, d.inverse()
    ({1: 2, 2: 3}, {2: 1, 3: 2})
    >>> d[1] = 3
    >>> d, d.inverse()
    ({1: 3}, {3: 1})
    >>> d.inverse()[2] = 4
    >>> d, d.inverse()
    ({1: 3, 4: 2}, {3: 1, 2: 4})
    >>> del d[1]
    >>> d, d.inverse()
    ({4: 2}, {2: 4})
    >>> d[4] = 2
    >>> d
    {4: 2}
    >>> d[2] = 2
    >>> d, d.inverse()
    ({2: 2}, {2: 2})
    """
    _forward:  dict[KT, VT]
    _backward: dict[VT, KT]

    def __init__(self, iterable: Iterable[tuple[KT, VT]] | dict[KT, VT] = ()) -> None:
        self._forward = dict(iterable)
        self._backward = {}

        for k, v in self._forward.items():
            self._backward[v] = k

    def inverse(self) -> "DoubleDict[VT, KT]":
        res = DoubleDict.__new__(DoubleDict)
        res._forward = self._backward
        res._backward = self._forward
        return res

    def __contains__(self, key: KT) -> bool:
        return key in self._forward

    def __getitem__(self, key: KT) -> VT:
        return self._forward[key]

    def __setitem__(self, key: KT, value: VT) -> None:
        if key in self and value == self[key]: return

        if key in self._forward:
            del self._backward[self._forward[key]]
        if value in self._backward:
            del self._forward[self._backward[value]]

        self._forward[key] = value
        self._backward[value] = key

    def __delitem__(self, key: KT) -> None:
        value = self._forward[key]
        del self._forward[key]
        del self._backward[value]

    def __iter__(self) -> Iterator[KT]:
        return iter(self._forward)

    def __len__(self) -> int:
        return len(self._forward)

    def __str__(self) -> str:
        return str(self._forward)

    def __repr__(self) -> str:
        return repr(self._forward)
