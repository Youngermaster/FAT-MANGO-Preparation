# Flatten (and Unflatten) a Nested Dictionary

> **Prompt as you will hear it:** *"Given `{"a": {"b": 1}}`, produce `{"a.b": 1}`. Handle arbitrary
> depth."*

---

## Why this one comes up so often

It is the most common *Python-specific* live-coding task, because it is real work: MongoDB update
documents use dot notation, config libraries merge nested YAML, Elasticsearch flattens documents,
and CSV export of JSON needs exactly this. It takes five minutes to get working and twenty to get
right, which makes it a perfect vehicle for edge-case questions.

What the interviewer is actually testing: **do you probe the edge cases before writing, or after
they point them out?**

---

## Files

| File | What it is |
|---|---|
| `flatten_dict.py` | `flatten`, `unflatten`, plus generator and iterative variants |
| `flatten_dict_cases.py` | The behaviour spec — 15 cases |
| `practice_flatten_dict.py` | Blank stub. **Start here.** |
| `test_flatten_dict.py` | Spec + cross-checks that all three variants agree |

```bash
uv run pytest 04-Live-Coding-Drills/03-flatten-nested-dict              # 22 pass
uv run pytest 04-Live-Coding-Drills/03-flatten-nested-dict -m practice  # your attempt
uv run python 04-Live-Coding-Drills/03-flatten-nested-dict/flatten_dict.py
```

---

## Walkthrough

### The core recursion

```python
for key, value in data.items():
    new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
    if isinstance(value, Mapping) and value:
        items.update(flatten(value, sep=sep, parent_key=new_key))
    else:
        items[new_key] = value
```

Eight lines. Everything interesting is in the conditions.

### The four traps

**1. `isinstance(value, Mapping)`, not `isinstance(value, dict)`.**
`Mapping` from `collections.abc` also matches `OrderedDict`, `defaultdict`, `ChainMap`, and any
user type registered as a mapping. Using the ABC instead of the concrete class is a small,
cheap senior signal.

**2. Empty containers must stay as leaves.**
Recursing into `{}` produces no keys at all, so `{"a": {}, "b": 1}` would flatten to `{"b": 1}` —
the key `a` silently deleted. The `and value` guard keeps it. Most candidates miss this; the spec
checks it.

**3. Never test truthiness of the value.**
`if value:` drops `None`, `0`, `False`, `""` and `[]` — all legitimate stored values. The check
must be about *type* (is it a mapping?), never about truthiness. `case_none_and_falsy_values_survive`
is the guard.

**4. Lists are a design decision, not an oversight.**
Say this out loud before writing: *"Do you want lists flattened by index, or treated as opaque
leaves?"* Both are defensible — config libraries treat them as leaves, MongoDB dot notation
indexes them — but asking is the senior move. The solution supports both via `flatten_lists`.

### The round trip is lossy, and you should say where

`unflatten(flatten(x)) == x` holds for dict-only structures. It does **not** hold once lists are
flattened by index, because `{"a": {"0": "x"}}` and `{"a": ["x"]}` flatten to the identical result.
Without a schema, `unflatten` cannot know which one to rebuild, so numeric segments come back as
string keys. Naming that limitation unprompted is worth more than handling it.

The other direction to guard: conflicting keys. `{"a": 1, "a.b": 2}` requires `a` to be both a
scalar and a mapping. Raise `ValueError` rather than silently letting the last write win.

And the separator is ambiguous if keys can contain it — `{"a.b": {"c": 1}}` and `{"a": {"b.c": 1}}`
collide. Real libraries either forbid separators in keys or escape them.

### The two variants worth knowing

**Generator version.** `flatten_iter` yields `(key, value)` pairs instead of building a dict, so a
caller can stream millions of rows into a database writer without materialising the flat dict.
`dict(flatten_iter(x))` recovers the eager version — building the lazy primitive and deriving the
eager one from it is the better factoring.

**Iterative version.** *"Now do it without recursion"* is the standard follow-up. Replace the call
stack with an explicit list of `(prefix, mapping)` pairs. The reason this matters beyond trivia:
Python's recursion limit is ~1000 frames, so deeply nested JSON crashes the recursive version with
`RecursionError` — a real denial-of-service vector for any endpoint accepting arbitrary payloads.
The test suite proves the point by building input 500 frames past the limit.

---

## Complexity

`O(n)` time and `O(n)` space in the number of leaf values, plus `O(d)` stack depth for the
recursive version where `d` is the nesting depth. String concatenation of key paths adds
`O(total key length)`.

---

## Follow-ups they will ask next

**"Deep-merge two nested dicts."** Same recursion, two inputs: when both sides have a mapping at
the same key, recurse; otherwise the right side wins. Decide explicitly what happens to lists
(replace or concatenate) — it is the same "ask first" moment as above.

**"Diff two nested dicts."** Flatten both, then compare key sets: `added = b.keys() - a.keys()`,
`removed = a.keys() - b.keys()`, `changed = {k for k in a.keys() & b.keys() if a[k] != b[k]}`.
Flattening first turns a tree diff into a set operation, which is a genuinely nice reduction to
show.

**"Where would you use this in a FastAPI service?"** Building a MongoDB `$set` document from a
PATCH payload: `{"$set": flatten(payload)}` updates nested fields without replacing whole
subdocuments. Pair it with `model_dump(exclude_unset=True)` so an absent field means "leave alone"
rather than "set to null" — that connection between Pydantic and Mongo semantics is exactly the
kind of thing this role is about.

---

## Say it out loud

> It is a recursion over the mapping: build the compound key, and if the value is itself a
> mapping, recurse with that key as the prefix, otherwise store it as a leaf. Three things I am
> careful about. I check `isinstance(value, Mapping)` from `collections.abc` rather than `dict`,
> so subclasses work. I keep empty dicts as leaves, because recursing into one produces no keys
> and would silently delete that branch. And I never test the value's truthiness, because `None`,
> zero, `False` and empty string are all real values. Lists are a question I would ask before
> writing — index them, or treat them as opaque leaves? Both are defensible. Unflattening is the
> inverse for dict-only structures, but once lists are indexed the round trip is lossy, since
> `{"a": {"0": "x"}}` and `{"a": ["x"]}` flatten identically. If they ask for a non-recursive
> version, I swap the call stack for an explicit stack — which also makes it safe against deeply
> nested JSON that would otherwise blow the recursion limit.
