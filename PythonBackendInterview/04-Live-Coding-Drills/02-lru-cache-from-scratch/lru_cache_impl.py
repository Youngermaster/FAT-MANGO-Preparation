"""LRU cache with O(1) get and put -- three implementations, from best-answer to from-scratch.

The interview move: reach for `OrderedDict` first (it shows stdlib fluency and takes 10 lines),
then say "and here is what it is doing underneath" and write the hashmap + doubly-linked-list
version. Doing both is what separates "knows Python" from "knows data structures".
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")

_MISSING = object()


# ==========================================================================================
# 1. The answer you give first: OrderedDict
# ==========================================================================================


class LRUCacheOrderedDict(Generic[K, V]):
    """LRU via `collections.OrderedDict`.

    `OrderedDict` is a dict that also maintains a doubly-linked list of its keys in insertion
    order -- which is exactly the structure an LRU needs, already written in C.

    - `move_to_end(key)` marks a key as most-recently-used, O(1).
    - `popitem(last=False)` evicts from the *front*, i.e. the least-recently-used, O(1).

    A plain `dict` also preserves insertion order (guaranteed since 3.7), but it has no
    `move_to_end` and no O(1) pop-from-front, so it cannot express "touch" or "evict oldest"
    cheaply. That distinction is a good thing to volunteer.
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data: OrderedDict[K, V] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: K, default: Any = None) -> Any:
        if key not in self._data:
            self.misses += 1
            return default
        self.hits += 1
        self._data.move_to_end(key)  # now the most-recently-used
        return self._data[key]

    def put(self, key: K, value: V) -> None:
        if key in self._data:
            # Updating an existing key counts as a use: refresh its recency.
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)  # evict least-recently-used

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        # Deliberately does NOT count as a use, and does not touch hit/miss stats.
        return key in self._data

    def keys_mru_first(self) -> list[K]:
        """Most-recently-used first. Test/debug helper, not part of the LRU contract."""
        return list(reversed(self._data))


# ==========================================================================================
# 2. The answer that proves you understand it: hashmap + doubly linked list
# ==========================================================================================


class _Node(Generic[K, V]):
    """One entry in the recency list.

    `__slots__` because a cache holds many of these: it drops the per-instance `__dict__`,
    saving roughly 40-50% of the memory per node and making attribute access slightly faster.
    A nice detail to mention unprompted.
    """

    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: K | None = None, value: V | None = None) -> None:
        self.key = key
        self.value = value
        self.prev: _Node[K, V] | None = None
        self.next: _Node[K, V] | None = None


class LRUCache(Generic[K, V]):
    """LRU cache with O(1) `get` and `put`, built from a dict and a doubly linked list.

    Why a *doubly* linked list: eviction needs to remove the tail, and a "touch" needs to
    unlink a node from the middle. Both require knowing the *previous* node, which a singly
    linked list cannot give you in O(1).

    Why sentinels: a permanent `head` and `tail` node mean no branch ever has to handle
    "the list is empty" or "this is the first/last element". Every unlink and every insert is
    the same four pointer assignments. This is where the classic bugs live, and sentinels
    delete the bugs rather than handling them.

    Layout:  head <-> (most recent) <-> ... <-> (least recent) <-> tail
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._map: dict[K, _Node[K, V]] = {}
        self._head: _Node[K, V] = _Node()  # sentinel: MRU side
        self._tail: _Node[K, V] = _Node()  # sentinel: LRU side
        self._head.next = self._tail
        self._tail.prev = self._head
        self.hits = 0
        self.misses = 0

    # -- list surgery -------------------------------------------------------------------

    def _unlink(self, node: _Node[K, V]) -> None:
        """Detach a node from the list. Both neighbours always exist thanks to the sentinels."""
        prev, nxt = node.prev, node.next
        assert prev is not None and nxt is not None
        prev.next = nxt
        nxt.prev = prev
        node.prev = node.next = None

    def _push_front(self, node: _Node[K, V]) -> None:
        """Insert right after head, i.e. mark as most-recently-used."""
        first = self._head.next
        assert first is not None
        node.prev = self._head
        node.next = first
        self._head.next = node
        first.prev = node

    # -- public API ---------------------------------------------------------------------

    def get(self, key: K, default: Any = None) -> Any:
        node = self._map.get(key)
        if node is None:
            self.misses += 1
            return default
        self.hits += 1
        self._unlink(node)
        self._push_front(node)
        return node.value

    def put(self, key: K, value: V) -> None:
        node = self._map.get(key)
        if node is not None:
            node.value = value
            self._unlink(node)
            self._push_front(node)
            return

        if len(self._map) >= self.capacity:
            self._evict()

        node = _Node(key, value)
        self._map[key] = node
        self._push_front(node)

    def _evict(self) -> None:
        """Drop the least-recently-used entry: the node just before the tail sentinel.

        THE CLASSIC BUG: unlinking the node from the list but forgetting to delete it from the
        dict. The cache then reports the key as present, hands back a node that is no longer in
        the recency list, and grows without bound. Both structures must stay in lockstep --
        every mutation touches the dict *and* the list.
        """
        lru = self._tail.prev
        assert lru is not None and lru is not self._head, "cannot evict from an empty cache"
        self._unlink(lru)
        assert lru.key is not None
        del self._map[lru.key]  # <-- the line people forget

    def __len__(self) -> int:
        return len(self._map)

    def __contains__(self, key: object) -> bool:
        return key in self._map

    def keys_mru_first(self) -> list[K]:
        out: list[K] = []
        node = self._head.next
        while node is not None and node is not self._tail:
            assert node.key is not None
            out.append(node.key)
            node = node.next
        return out


if __name__ == "__main__":
    for name, cls in [("OrderedDict", LRUCacheOrderedDict), ("linked list", LRUCache)]:
        cache: Any = cls(capacity=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")  # touch 'a', so 'b' is now the coldest
        cache.put("d", 4)  # evicts 'b'

        print(
            f"{name:>12}: MRU-first {cache.keys_mru_first()}  "
            f"'b' evicted: {'b' not in cache}  hits={cache.hits} misses={cache.misses}"
        )

    # Both orderings agree, which is the point: the OrderedDict version is the same algorithm
    # with the linked list hidden inside the C implementation.
