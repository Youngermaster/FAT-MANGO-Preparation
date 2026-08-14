"""Spec run against both reference implementations, and against your practice stub."""

from __future__ import annotations

from typing import Any

import lru_cache_cases as spec
import pytest
from lru_cache_impl import LRUCache, LRUCacheOrderedDict
from practice_lru_cache import LRUCache as PracticeLRUCache

_ids = lambda c: c.__name__[len("case_") :]  # noqa: E731


@pytest.mark.parametrize(
    "cache_cls", [LRUCache, LRUCacheOrderedDict], ids=["linkedlist", "ordereddict"]
)
@pytest.mark.parametrize("case", spec.CASES, ids=_ids)
def test_solution(case: Any, cache_cls: Any) -> None:
    case(cache_cls)


@pytest.mark.practice
@pytest.mark.parametrize("case", spec.CASES, ids=_ids)
def test_practice(case: Any) -> None:
    case(PracticeLRUCache)
