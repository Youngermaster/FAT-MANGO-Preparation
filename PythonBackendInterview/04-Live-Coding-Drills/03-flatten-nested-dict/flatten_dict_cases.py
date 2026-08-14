"""Behaviour spec for flatten/unflatten. Each case takes the two functions under test."""

from __future__ import annotations

from typing import Any

import pytest


def case_flat_input_is_unchanged(flatten: Any, unflatten: Any) -> None:
    assert flatten({"a": 1, "b": 2}) == {"a": 1, "b": 2}


def case_single_level_of_nesting(flatten: Any, unflatten: Any) -> None:
    assert flatten({"a": {"b": 1}}) == {"a.b": 1}


def case_deep_nesting(flatten: Any, unflatten: Any) -> None:
    assert flatten({"a": {"b": {"c": {"d": 1}}}}) == {"a.b.c.d": 1}


def case_mixed_depths(flatten: Any, unflatten: Any) -> None:
    assert flatten({"a": 1, "b": {"c": 2, "d": {"e": 3}}}) == {"a": 1, "b.c": 2, "b.d.e": 3}


def case_custom_separator(flatten: Any, unflatten: Any) -> None:
    assert flatten({"a": {"b": 1}}, sep="__") == {"a__b": 1}
    assert unflatten({"a__b": 1}, sep="__") == {"a": {"b": 1}}


def case_empty_dict(flatten: Any, unflatten: Any) -> None:
    assert flatten({}) == {}
    assert unflatten({}) == {}


def case_empty_nested_dict_is_kept_as_a_leaf(flatten: Any, unflatten: Any) -> None:
    """Recursing into `{}` yields no keys, which would silently delete `a` entirely."""
    assert flatten({"a": {}, "b": 1}) == {"a": {}, "b": 1}


def case_lists_are_opaque_by_default(flatten: Any, unflatten: Any) -> None:
    assert flatten({"a": [1, 2, {"b": 3}]}) == {"a": [1, 2, {"b": 3}]}


def case_lists_can_be_flattened_by_index(flatten: Any, unflatten: Any) -> None:
    assert flatten({"a": ["x", "y"]}, flatten_lists=True) == {"a.0": "x", "a.1": "y"}


def case_lists_of_dicts_flatten_recursively(flatten: Any, unflatten: Any) -> None:
    got = flatten({"items": [{"id": 1}, {"id": 2}]}, flatten_lists=True)
    assert got == {"items.0.id": 1, "items.1.id": 2}


def case_none_and_falsy_values_survive(flatten: Any, unflatten: Any) -> None:
    """`if value:` instead of an explicit type check would drop every one of these."""
    data = {"a": None, "b": 0, "c": False, "d": "", "e": []}
    assert flatten(data) == data


def case_unflatten_inverts_flatten(flatten: Any, unflatten: Any) -> None:
    nested = {"a": 1, "b": {"c": 2, "d": {"e": [1, 2]}}, "f": {}}
    assert unflatten(flatten(nested)) == nested


def case_unflatten_rejects_conflicting_shapes(flatten: Any, unflatten: Any) -> None:
    """`a` cannot be both a scalar and a mapping."""
    with pytest.raises(ValueError):
        unflatten({"a": 1, "a.b": 2})


def case_unflatten_rejects_overwriting_a_subtree(flatten: Any, unflatten: Any) -> None:
    with pytest.raises(ValueError):
        unflatten({"a.b": 2, "a": 1})


def case_non_string_keys_are_stringified(flatten: Any, unflatten: Any) -> None:
    assert flatten({1: {2: "x"}}) == {"1.2": "x"}


CASES = [
    case_flat_input_is_unchanged,
    case_single_level_of_nesting,
    case_deep_nesting,
    case_mixed_depths,
    case_custom_separator,
    case_empty_dict,
    case_empty_nested_dict_is_kept_as_a_leaf,
    case_lists_are_opaque_by_default,
    case_lists_can_be_flattened_by_index,
    case_lists_of_dicts_flatten_recursively,
    case_none_and_falsy_values_survive,
    case_unflatten_inverts_flatten,
    case_unflatten_rejects_conflicting_shapes,
    case_unflatten_rejects_overwriting_a_subtree,
    case_non_string_keys_are_stringified,
]
