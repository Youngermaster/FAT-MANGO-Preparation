"""PRACTICE STUB -- flatten and unflatten from scratch.

    uv run pytest 04-Live-Coding-Drills/03-flatten-nested-dict -m practice

Budget: 10 minutes for `flatten`, 10 more for `unflatten`.

The traps the spec checks for:
  - `{"a": {}}` must keep `a` as a leaf, not vanish
  - `None`, `0`, `False`, `""`, `[]` are values, not absences -- do not test truthiness
  - lists are opaque leaves unless `flatten_lists=True`, then they get numeric segments
  - non-string keys get stringified
  - `unflatten` raises ValueError when keys disagree about the tree shape
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def flatten(
    data: Mapping[str, Any],
    *,
    sep: str = ".",
    flatten_lists: bool = False,
    parent_key: str = "",
) -> dict[str, Any]:
    """Flatten a nested mapping into one level of separator-joined keys."""
    raise NotImplementedError("Write me from scratch. No peeking, no autocomplete.")


def unflatten(data: Mapping[str, Any], *, sep: str = ".") -> dict[str, Any]:
    """Rebuild a nested dict from separator-joined keys."""
    raise NotImplementedError


if __name__ == "__main__":
    nested = {"user": {"name": "Ada", "address": {"city": "London"}}, "active": True}
    flat = flatten(nested)
    print("flat      :", flat)
    print("round trip:", unflatten(flat) == nested)
