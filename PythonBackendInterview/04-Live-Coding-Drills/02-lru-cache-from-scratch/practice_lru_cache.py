"""PRACTICE STUB -- build the hashmap + doubly-linked-list version from scratch.

    uv run pytest 04-Live-Coding-Drills/02-lru-cache-from-scratch -m practice

Budget: 15 minutes. Do the `OrderedDict` version first in your head (it is 10 lines), then
write the linked-list one here -- that is the version the interviewer actually wants to see.

Required API (each line maps to at least one test):
  LRUCache(capacity)        raises ValueError if capacity <= 0
  .get(key, default=None)   O(1); a hit refreshes recency and increments .hits
                            a miss increments .misses and returns default
  .put(key, value)          O(1); updating an existing key refreshes recency and does NOT grow
                            len(); exceeding capacity evicts the least-recently-used entry
  .hits / .misses           counters
  len(cache)                current entry count
  key in cache              membership WITHOUT counting as a use
  .keys_mru_first()         list of keys, most-recently-used first

Design reminders:
  - Doubly linked, not singly: unlinking a middle node needs its predecessor in O(1).
  - Use head/tail sentinel nodes so no branch has to special-case an empty list.
  - On eviction, remove the node from the list AND delete the key from the dict. Forgetting
    the second half is THE classic bug and `case_eviction_removes_from_both_structures`
    is watching for it.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class _Node(Generic[K, V]):
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: K | None = None, value: V | None = None) -> None:
        self.key = key
        self.value = value
        self.prev: _Node[K, V] | None = None
        self.next: _Node[K, V] | None = None


class LRUCache(Generic[K, V]):
    """O(1) get/put LRU cache."""

    def __init__(self, capacity: int) -> None:
        raise NotImplementedError("Write me from scratch. No peeking, no autocomplete.")

    def get(self, key: K, default: Any = None) -> Any:
        raise NotImplementedError

    def put(self, key: K, value: V) -> None:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError

    def __contains__(self, key: object) -> bool:
        raise NotImplementedError

    def keys_mru_first(self) -> list[K]:
        raise NotImplementedError


if __name__ == "__main__":
    c: Any = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    c.get("a")
    c.put("d", 4)
    print("MRU-first:", c.keys_mru_first(), "| 'b' evicted:", "b" not in c)
