"""Flatten and unflatten arbitrarily nested dictionaries.

A staple of Python-specific rounds because it is genuinely useful (config merging, MongoDB dot
notation, CSV export of JSON, Elasticsearch documents) and because it has one deep question
hiding inside it: how do you handle lists, and what happens on a round trip?
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, MutableMapping
from typing import Any


def flatten(
    data: Mapping[str, Any],
    *,
    sep: str = ".",
    flatten_lists: bool = False,
    parent_key: str = "",
) -> dict[str, Any]:
    """Flatten a nested mapping into a single level of dotted keys.

        {"a": {"b": 1}} -> {"a.b": 1}

    Args:
        data: The mapping to flatten.
        sep: Separator between path segments.
        flatten_lists: If True, list elements get numeric segments (`items.0.name`), which makes
            the transform lossless and round-trippable. If False (the default, and what most
            config libraries do) lists are treated as opaque leaf values.
        parent_key: Prefix for recursion. Callers leave this alone.

    Returns:
        A flat dict. Empty containers become leaves rather than vanishing -- see below.

    Note:
        An empty dict or list is kept as a *value* (`{"a": {}}` -> `{"a": {}}`) rather than
        disappearing. Recursing into it would produce no keys at all and silently lose the fact
        that `a` existed. Interviewers like this one because most candidates drop the key.
    """
    items: dict[str, Any] = {}

    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)

        if isinstance(value, Mapping) and value:
            items.update(flatten(value, sep=sep, flatten_lists=flatten_lists, parent_key=new_key))
        elif flatten_lists and isinstance(value, list) and value:
            for index, element in enumerate(value):
                indexed_key = f"{new_key}{sep}{index}"
                if isinstance(element, Mapping) and element:
                    items.update(
                        flatten(element, sep=sep, flatten_lists=True, parent_key=indexed_key)
                    )
                else:
                    items[indexed_key] = element
        else:
            # Leaf: scalars, empty containers, and (when flatten_lists is False) every list.
            items[new_key] = value

    return items


def unflatten(data: Mapping[str, Any], *, sep: str = ".") -> dict[str, Any]:
    """Rebuild a nested dict from dotted keys. Inverse of `flatten` for dict-only structures.

    Numeric segments stay *string keys*, not list indices -- `unflatten(flatten(x))` cannot
    reconstruct lists without a schema, because `{"a": {"0": "x"}}` and `{"a": ["x"]}` flatten
    to the identical thing. Saying that out loud is the point of the exercise: the transform is
    lossy in one direction and you should know exactly where.

    Raises:
        ValueError: If two keys disagree about the shape of the tree, e.g. `{"a": 1, "a.b": 2}`
            requires `a` to be both a scalar and a mapping.
    """
    result: dict[str, Any] = {}

    for compound_key, value in data.items():
        parts = compound_key.split(sep)
        cursor = result

        for part in parts[:-1]:
            existing = cursor.get(part)
            if existing is None and part not in cursor:
                cursor[part] = {}
            elif not isinstance(existing, MutableMapping):
                raise ValueError(
                    f"conflicting keys: {compound_key!r} needs {part!r} to be a mapping, "
                    f"but it is already {type(existing).__name__}"
                )
            cursor = cursor[part]

        last = parts[-1]
        if isinstance(cursor.get(last), MutableMapping) and cursor.get(last):
            raise ValueError(f"conflicting keys: {compound_key!r} would overwrite a subtree")
        cursor[last] = value

    return result


def flatten_iter(
    data: Mapping[str, Any], *, sep: str = ".", parent_key: str = ""
) -> Iterator[tuple[str, Any]]:
    """Generator variant: yields pairs instead of building a dict.

    Worth showing when the input is large -- the caller can stream straight into a database
    writer without materialising the whole flat dict. `dict(flatten_iter(x))` recovers the
    eager version, which is a nice demonstration of building the lazy primitive first.
    """
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
        if isinstance(value, Mapping) and value:
            yield from flatten_iter(value, sep=sep, parent_key=new_key)
        else:
            yield new_key, value


def flatten_iterative(data: Mapping[str, Any], *, sep: str = ".") -> dict[str, Any]:
    """Explicit-stack version, for when they ask 'now do it without recursion'.

    Python's default recursion limit is 1000 frames, so the recursive version dies on inputs
    nested ~1000 deep. That is not a realistic config file, but it *is* a realistic attack on
    an endpoint that accepts arbitrary JSON -- which is the real reason to know this variant.
    """
    out: dict[str, Any] = {}
    stack: list[tuple[str, Any]] = [("", data)]

    while stack:
        prefix, current = stack.pop()
        for key, value in current.items():
            new_key = f"{prefix}{sep}{key}" if prefix else str(key)
            if isinstance(value, Mapping) and value:
                stack.append((new_key, value))
            else:
                out[new_key] = value

    return out


if __name__ == "__main__":
    nested = {
        "user": {
            "name": "Ada",
            "address": {"city": "London", "zip": "N1"},
            "tags": ["admin", "beta"],
        },
        "active": True,
        "meta": {},
    }

    flat = flatten(nested)
    print("flat            :", flat)
    print("lists flattened :", flatten(nested, flatten_lists=True))
    print("custom separator:", flatten(nested, sep="__"))
    print("round trip ok   :", unflatten(flat) == nested)
    print("iterative agrees:", flatten_iterative(nested) == flat)
    print("generator agrees:", dict(flatten_iter(nested)) == flat)

    # The lossy direction: numeric segments come back as string keys, not lists.
    round_tripped = unflatten(flatten(nested, flatten_lists=True))
    print("lists survive?  :", round_tripped["user"]["tags"], "<- dict, not list")

    try:
        unflatten({"a": 1, "a.b": 2})
    except ValueError as exc:
        print("conflict caught :", exc)
