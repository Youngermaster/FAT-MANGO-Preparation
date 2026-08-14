"""Pins every gotcha, so the claims in the README are verified rather than remembered."""

from __future__ import annotations

import copy
import sys

import pytest
from gotchas import (
    BrokenAccount,
    ConfigBroken,
    FixedAccount,
    append_broken,
    append_fixed,
    make_broken_callbacks,
    make_fixed_callbacks_default_arg,
    make_fixed_callbacks_partial,
)

# ------------------------------------------------------------------------------------------
# Mutable default arguments
# ------------------------------------------------------------------------------------------


def test_mutable_default_accumulates_across_calls() -> None:
    # Reset the shared default so this test is independent of import order / other tests.
    append_broken.__defaults__[0].clear()

    assert append_broken(1) == [1]
    assert append_broken(2) == [1, 2], "the SAME list is reused on every call"
    assert append_broken(3) == [1, 2, 3]


def test_the_default_object_is_created_once_at_def_time() -> None:
    """The mechanism, not just the symptom: the default lives on the function object."""
    append_broken.__defaults__[0].clear()
    append_broken(7)
    assert append_broken.__defaults__ == ([7],)


def test_none_sentinel_fixes_it() -> None:
    assert append_fixed(1) == [1]
    assert append_fixed(2) == [2]
    assert append_fixed(3) == [3]


def test_explicitly_passed_list_is_still_used() -> None:
    mine: list[int] = []
    assert append_fixed(1, mine) is mine
    assert mine == [1]


def test_dataclass_rejects_a_mutable_default_at_class_creation() -> None:
    """Dataclasses turn this bug into an immediate error instead of a runtime surprise."""
    with pytest.raises(ValueError, match="mutable default"):
        from dataclasses import dataclass

        @dataclass
        class Bad:
            tags: list[str] = []  # noqa: RUF008


def test_default_factory_gives_each_instance_its_own_list() -> None:
    a, b = ConfigBroken(), ConfigBroken()
    a.tags.append("x")
    assert b.tags == []


# ------------------------------------------------------------------------------------------
# Late-binding closures
# ------------------------------------------------------------------------------------------


def test_late_binding_makes_every_closure_return_the_last_value() -> None:
    assert [f() for f in make_broken_callbacks()] == [4, 4, 4, 4, 4]


@pytest.mark.parametrize(
    "factory", [make_fixed_callbacks_default_arg, make_fixed_callbacks_partial]
)
def test_both_fixes_bind_the_value_at_creation_time(factory) -> None:  # noqa: ANN001
    assert [f() for f in factory()] == [0, 1, 2, 3, 4]


def test_the_closure_shares_the_variable_not_the_value() -> None:
    """Shows the mechanism: closures capture the cell, and the cell is mutable.

    The `noqa` is the point in miniature -- ruff's B023 flags this pattern automatically.
    """
    funcs = []
    for i in range(3):
        funcs.append(lambda: i)  # noqa: B023
    assert [f() for f in funcs] == [2, 2, 2]
    # And the closure cell really does hold the final binding:
    assert funcs[0].__closure__ is None or funcs[0]() == 2


# ------------------------------------------------------------------------------------------
# Identity vs equality
# ------------------------------------------------------------------------------------------


def test_small_ints_are_cached() -> None:
    """-5..256 are pre-created at startup and shared, so `is` accidentally works there.

    Note the values are built at runtime via `int(str)`; writing `256 is 256` directly is a
    SyntaxWarning in modern Python precisely because it is such a common mistake.
    """
    cached = 256
    assert int("256") is cached


def test_large_ints_are_not_cached() -> None:
    outside_cache = 257
    assert int("257") is not outside_cache
    assert int("257") == outside_cache


def test_runtime_built_strings_are_not_interned() -> None:
    literal = "hello"
    built = "".join(["hel", "lo"])
    assert built is not literal, "only compile-time literals are interned"
    assert built == literal


def test_is_is_correct_for_singletons() -> None:
    """The rule: `is` for None/True/False/sentinels only."""
    value = None
    assert value is None
    sentinel = object()
    assert sentinel is not object()


# ------------------------------------------------------------------------------------------
# Copying
# ------------------------------------------------------------------------------------------


def test_shallow_copy_shares_inner_objects() -> None:
    original = [[1, 2], [3, 4]]
    shallow = copy.copy(original)

    assert shallow is not original, "the outer container IS new"
    assert shallow[0] is original[0], "but the inner objects are shared"

    shallow[0].append(99)
    assert original[0] == [1, 2, 99], "which is why the original changed"


def test_deep_copy_duplicates_everything() -> None:
    original = [[1, 2], [3, 4]]
    deep = copy.deepcopy(original)

    assert deep[0] is not original[0]
    deep[0].append(99)
    assert original[0] == [1, 2]


def test_dict_copy_is_shallow_too() -> None:
    """The practical version: nested config dicts are the usual victim."""
    config = {"db": {"host": "localhost"}}
    clone = config.copy()
    clone["db"]["host"] = "prod"
    assert config["db"]["host"] == "prod", "dict.copy() does not protect nested values"


# ------------------------------------------------------------------------------------------
# Class vs instance attributes
# ------------------------------------------------------------------------------------------


def test_class_attribute_is_shared_between_instances() -> None:
    BrokenAccount.transactions.clear()
    a, b = BrokenAccount(), BrokenAccount()
    a.add("from a")
    assert b.transactions == ["from a"], "both instances mutate the one class-level list"
    BrokenAccount.transactions.clear()


def test_instance_attribute_is_per_object() -> None:
    a, b = FixedAccount(), FixedAccount()
    a.add("from a")
    assert b.transactions == []


def test_rebinding_creates_an_instance_attribute_that_shadows_the_class_one() -> None:
    """The subtlety: `self.x.append(...)` mutates the shared object, `self.x = [...]` does not."""
    BrokenAccount.transactions.clear()
    a = BrokenAccount()
    a.transactions = ["own"]  # rebinding, not mutating
    assert BrokenAccount.transactions == []
    assert "transactions" in a.__dict__


# ------------------------------------------------------------------------------------------
# Truthiness
# ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", [0, 0.0, "", [], {}, set(), False])
def test_falsy_values_are_not_none(value: object) -> None:
    assert not value
    assert value is not None


# ------------------------------------------------------------------------------------------
# Immortal objects
# ------------------------------------------------------------------------------------------


@pytest.mark.skipif(sys.version_info < (3, 12), reason="immortal objects are 3.12+")
def test_small_ints_are_immortal() -> None:
    """PEP 683: the refcount is a sentinel, not a count -- groundwork for free-threading."""
    assert sys.getrefcount(1) > 2**30
