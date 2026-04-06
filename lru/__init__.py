"""Small pure-Python LRU compatibility shim for local tests.

This exists so Home Assistant's test runtime can import `lru.LRU` in this
environment, where the compiled `lru-dict` dependency cannot be built because a
system C compiler is unavailable.

It is intentionally minimal and only implements the mapping behavior needed by
the Home Assistant test harness.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator, MutableMapping
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LRU(MutableMapping[K, V], Generic[K, V]):
    """Simple least-recently-used mapping."""

    def __init__(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._maxsize = maxsize
        self._data: OrderedDict[K, V] = OrderedDict()

    def __getitem__(self, key: K) -> V:
        value = self._data[key]
        self._data.move_to_end(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def __delitem__(self, key: K) -> None:
        del self._data[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def clear(self) -> None:
        self._data.clear()

    def get(self, key: K, default: V | None = None) -> V | None:
        if key not in self._data:
            return default
        return self[key]

    def __contains__(self, key: object) -> bool:
        return key in self._data
