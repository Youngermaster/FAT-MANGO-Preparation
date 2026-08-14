"""Behaviour spec for an LRU cache, shared by the solution and practice suites.

Every `case_*` takes the cache *class* under test.
"""

from __future__ import annotations

from typing import Any

import pytest


def case_stores_and_retrieves(cache_cls: Any) -> None:
    c = cache_cls(2)
    c.put("a", 1)
    assert c.get("a") == 1


def case_missing_key_returns_default(cache_cls: Any) -> None:
    c = cache_cls(2)
    assert c.get("nope") is None
    assert c.get("nope", "fallback") == "fallback"


def case_evicts_least_recently_used(cache_cls: Any) -> None:
    c = cache_cls(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)  # capacity exceeded -> 'a' is coldest, so 'a' goes
    assert "a" not in c
    assert c.get("b") == 2
    assert c.get("c") == 3
    assert len(c) == 2


def case_get_refreshes_recency(cache_cls: Any) -> None:
    """The defining behaviour: reading a key makes it the newest."""
    c = cache_cls(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")     # 'a' is now newest, 'b' is coldest
    c.put("c", 3)  # so 'b' is evicted, NOT 'a'
    assert "b" not in c
    assert c.get("a") == 1


def case_put_of_existing_key_refreshes_recency(cache_cls: Any) -> None:
    c = cache_cls(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 99)  # an update is a use
    c.put("c", 3)
    assert "b" not in c
    assert c.get("a") == 99


def case_updating_does_not_grow_the_cache(cache_cls: Any) -> None:
    c = cache_cls(2)
    c.put("a", 1)
    c.put("a", 2)
    c.put("a", 3)
    assert len(c) == 1
    assert c.get("a") == 3


def case_never_exceeds_capacity(cache_cls: Any) -> None:
    c = cache_cls(3)
    for i in range(100):
        c.put(i, i)
        assert len(c) <= 3
    assert len(c) == 3


def case_eviction_removes_from_both_structures(cache_cls: Any) -> None:
    """Catches the classic bug: unlinked from the list but left in the dict.

    If eviction forgets the dict, `len()` keeps climbing and the evicted key still reports as
    present -- an unbounded memory leak wearing a cache's clothes.
    """
    c = cache_cls(2)
    for i in range(50):
        c.put(i, i)
    assert len(c) == 2
    assert sum(1 for i in range(50) if i in c) == 2


def case_capacity_one(cache_cls: Any) -> None:
    c = cache_cls(1)
    c.put("a", 1)
    c.put("b", 2)
    assert "a" not in c
    assert c.get("b") == 2


def case_rejects_non_positive_capacity(cache_cls: Any) -> None:
    with pytest.raises(ValueError):
        cache_cls(0)
    with pytest.raises(ValueError):
        cache_cls(-1)


def case_none_is_a_storable_value(cache_cls: Any) -> None:
    """`None` stored is indistinguishable from `None` missing via `get` alone.

    That ambiguity is real and worth naming in the interview: it is why `__contains__` exists
    and why `functools.lru_cache` uses a private sentinel internally.
    """
    c = cache_cls(2)
    c.put("a", None)
    assert c.get("a") is None
    assert "a" in c
    assert "b" not in c


def case_tracks_hits_and_misses(cache_cls: Any) -> None:
    c = cache_cls(2)
    c.put("a", 1)
    c.get("a")
    c.get("a")
    c.get("zzz")
    assert c.hits == 2
    assert c.misses == 1


def case_mru_ordering_is_reported_correctly(cache_cls: Any) -> None:
    c = cache_cls(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.keys_mru_first() == ["c", "b", "a"]
    c.get("a")
    assert c.keys_mru_first() == ["a", "c", "b"]


def case_survives_a_long_mixed_workload(cache_cls: Any) -> None:
    """Cross-check against a brute-force reference model over a deterministic workload."""
    import random

    rng = random.Random(20260814)
    capacity = 8
    c = cache_cls(capacity)
    model: list[Any] = []  # MRU-first list of keys, the obviously-correct slow version

    for _ in range(2000):
        key = rng.randrange(20)
        if rng.random() < 0.5:
            c.put(key, key * 10)
            if key in model:
                model.remove(key)
            model.insert(0, key)
            if len(model) > capacity:
                model.pop()
        else:
            got = c.get(key)
            if key in model:
                assert got == key * 10
                model.remove(key)
                model.insert(0, key)
            else:
                assert got is None

        assert c.keys_mru_first() == model

    assert len(c) == len(model)


CASES = [
    case_stores_and_retrieves,
    case_missing_key_returns_default,
    case_evicts_least_recently_used,
    case_get_refreshes_recency,
    case_put_of_existing_key_refreshes_recency,
    case_updating_does_not_grow_the_cache,
    case_never_exceeds_capacity,
    case_eviction_removes_from_both_structures,
    case_capacity_one,
    case_rejects_non_positive_capacity,
    case_none_is_a_storable_value,
    case_tracks_hits_and_misses,
    case_mru_ordering_is_reported_correctly,
    case_survives_a_long_mixed_workload,
]
