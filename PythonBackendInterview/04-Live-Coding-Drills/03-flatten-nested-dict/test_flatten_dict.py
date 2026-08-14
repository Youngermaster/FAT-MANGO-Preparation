"""Spec run against the solution and against your practice stub."""

from __future__ import annotations

import sys
from typing import Any

import flatten_dict_cases as spec
import practice_flatten_dict
import pytest
from flatten_dict import flatten, flatten_iter, flatten_iterative, unflatten

_ids = lambda c: c.__name__[len("case_") :]  # noqa: E731


@pytest.mark.parametrize("case", spec.CASES, ids=_ids)
def test_solution(case: Any) -> None:
    case(flatten, unflatten)


@pytest.mark.practice
@pytest.mark.parametrize("case", spec.CASES, ids=_ids)
def test_practice(case: Any) -> None:
    case(practice_flatten_dict.flatten, practice_flatten_dict.unflatten)


# --- the alternative implementations must agree with the recursive one -------------------


@pytest.mark.parametrize(
    "nested",
    [
        {"a": 1},
        {"a": {"b": {"c": 1}}, "d": 2},
        {"a": {}, "b": None, "c": [1, 2]},
    ],
)
def test_generator_variant_matches(nested: dict[str, Any]) -> None:
    assert dict(flatten_iter(nested)) == flatten(nested)


@pytest.mark.parametrize(
    "nested",
    [
        {"a": 1},
        {"a": {"b": {"c": 1}}, "d": 2},
        {"a": {}, "b": None, "c": [1, 2]},
    ],
)
def test_iterative_variant_matches(nested: dict[str, Any]) -> None:
    assert flatten_iterative(nested) == flatten(nested)


def test_iterative_variant_survives_input_that_overflows_recursion() -> None:
    """The reason the explicit-stack version exists.

    Deeply nested JSON is a real attack on any endpoint that accepts arbitrary payloads: the
    recursive version raises RecursionError, the iterative one does not.
    """
    depth = sys.getrecursionlimit() + 500
    deep: dict[str, Any] = {"leaf": 1}
    for _ in range(depth):
        deep = {"n": deep}

    with pytest.raises(RecursionError):
        flatten(deep)

    flat = flatten_iterative(deep)
    assert len(flat) == 1
    assert next(iter(flat.values())) == 1
