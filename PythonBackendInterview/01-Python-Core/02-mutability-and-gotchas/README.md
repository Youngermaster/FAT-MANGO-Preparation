# Mutability, Closures, Identity — the "What Does This Print?" Round

> **Prompt as you will hear it:** *"What does this print, and why?"* — followed by four or five
> short snippets.

These look like trivia. They are not. Each one is a bug that ships:

- The **mutable default** is shared state leaking across requests in a web service.
- The **late-binding closure** is the bug in every loop that builds callbacks or handlers.
- **Shallow copy** is why "I copied the config and it still changed".
- **Falsy vs `None`** is how a legitimate `0` silently becomes a default.

---

## Run it

```bash
uv run python 01-Python-Core/02-mutability-and-gotchas/gotchas.py
uv run pytest 01-Python-Core/02-mutability-and-gotchas    # 28 tests
```

---

## 1. Mutable default arguments

```python
def append(item, target=[]):  # BUG
    target.append(item)
    return target


append(1)  # [1]
append(2)  # [1, 2]   <- same list!
append(3)  # [1, 2, 3]
```

**Why:** default values are evaluated **once, when the `def` statement executes** — not per call.
The list is stored on the function object itself. You can watch it happen:

```python
>>> append.__defaults__
([1, 2, 3],)
```

Showing `__defaults__` is the difference between "I memorised this" and "I understand this". It is
the single best 10 seconds you can spend on this question.

**The fix:**

```python
def append(item, target=None):
    if target is None:
        target = []
```

Use `None` as the sentinel. When `None` is itself a legitimate value the caller might pass, use a
private module-level sentinel (`_MISSING = object()`) — which is exactly what `functools` and
`dataclasses` do internally.

**Bonus point:** dataclasses turn this into an immediate error rather than a runtime surprise —
`tags: list[str] = []` raises `ValueError: mutable default` at *class creation* time. Use
`field(default_factory=list)`. Pydantic does the same thing.

---

## 2. Late-binding closures

```python
funcs = [lambda: i for i in range(5)]
[f() for f in funcs]  # [4, 4, 4, 4, 4]  -- not [0, 1, 2, 3, 4]
```

**Why:** the lambda closes over the **variable**, not its value. All five share one closure cell,
and by the time any of them runs the loop is over and `i` is 4. Python closures are late-binding
by design — the value is read when the function is *called*, not when it is *created*.

Two fixes:

```python
[lambda i=i: i for i in range(5)]  # default args ARE evaluated at def time
[partial(identity, i) for i in range(5)]  # explicit binding, arguably clearer
```

**Why it matters in real code:** every `for` loop that builds event handlers, retry callbacks,
route handlers, or `asyncio` tasks from a loop variable. It is the most common source of "all my
handlers do the same thing".

---

## 3. `is` vs `==`

`is` compares **identity** (same object in memory); `==` compares **value**.

The confusion comes from CPython caching, which makes `is` accidentally work sometimes:

| Expression | Result | Why |
|---|---|---|
| `int("256") is 256` | `True` | small ints −5..256 are pre-created and shared |
| `int("257") is 257` | `False` | outside the cache |
| `"hello" is "hel" + "lo"` | `True` | constant-folded and interned at compile time |
| `"hello" is "".join(["hel","lo"])` | `False` | built at runtime, not interned |

**The rule to state:** use `is` **only** for singletons — `None`, `True`, `False`, and sentinel
objects. Never for numbers or strings, whatever the REPL appeared to tell you.

Modern Python helps: writing `x is 256` literally is now a `SyntaxWarning` — *"is" with 'int'
literal. Did you mean "=="?*

---

## 4. Shallow vs deep copy

```python
original = [[1, 2], [3, 4]]
shallow = copy.copy(original)
shallow[0].append(99)
original  # [[1, 2, 99], [3, 4]]   <- changed!
```

A shallow copy duplicates the **outer** container and **shares the inner objects**. Three distinct
things:

| | New outer? | New inner? |
|---|---|---|
| `b = a` | no | no |
| `copy.copy(a)`, `a.copy()`, `a[:]`, `dict(a)` | yes | **no** |
| `copy.deepcopy(a)` | yes | yes |

The practical version: **`dict.copy()` does not protect nested config.** That is the bug people
actually hit.

`deepcopy` is not free — it walks the whole object graph and is slow on large structures (it also
handles cycles via a memo dict). For nested config the better answer is often immutability: frozen
dataclasses, or Pydantic models with `model_config = ConfigDict(frozen=True)`.

---

## 5. Class vs instance attributes

```python
class Account:
    transactions = []  # BUG: one list shared by every instance

    def add(self, item):
        self.transactions.append(item)  # mutates the CLASS-level list
```

`a.add("x")` is visible from `b`. The fix is to create it per instance in `__init__`.

The subtlety worth knowing: `self.transactions.append(...)` **mutates** the shared object, but
`self.transactions = [...]` **rebinds** — creating an instance attribute that shadows the class
one and leaves the class attribute untouched. Tested, because that asymmetry is exactly what makes
the bug confusing.

---

## 6. Falsy is not `None`

`0`, `0.0`, `""`, `[]`, `{}`, `set()`, `False` are all falsy and none of them are `None`.

```python
def paginate(limit=None):
    limit = limit or 50  # BUG: limit=0 silently becomes 50
    limit = 50 if limit is None else limit  # correct
```

This is the same mistake as testing truthiness in `flatten` (see
`04-Live-Coding-Drills/03-flatten-nested-dict`). If you mean "was it provided?", test `is None`.

---

## 7. A current detail: immortal objects

```python
>>> sys.getrefcount(1)
4294967295
```

That is **not** "lots of references" — it is the sentinel for an **immortal object** (PEP 683,
Python 3.12). Small ints, `None`, `True`/`False` and interned strings are marked so their
reference counts are never updated.

**Why:** refcount updates are memory *writes*, and writes to shared objects dirty CPU cache lines
across cores. Skipping them for the hottest shared objects is groundwork for per-interpreter GIL
(PEP 684) and free-threaded Python (PEP 703).

Dropping this connects three topics at once — memory management, the GIL, and 3.13/3.14
free-threading — and very few candidates will mention it.

---

## Follow-ups they will ask next

**"Which types are immutable?"** `int`, `float`, `str`, `bytes`, `tuple`, `frozenset`, `bool`,
`None`. Mutable: `list`, `dict`, `set`, `bytearray`, and most user classes. The consequence:
**only hashable (effectively immutable) objects can be dict keys or set members**, because
mutating a key would strand it in the wrong hash bucket.

**"Is a tuple always hashable?"** No — `hash((1, [2]))` raises. A tuple's hash is derived from its
contents, so it is hashable only if everything inside is.

**"What about `+=` on a tuple inside a dict?"** `d["k"] += [1]` where the value is a tuple raises
`TypeError` *and* mutates — a famous Python oddity worth knowing exists.

**"How do you make a value object safely?"** `@dataclass(frozen=True, slots=True)` — immutable,
hashable, memory-efficient. See `01-Python-Core/09-dunders-slots-dataclasses/`.

---

## Say it out loud

> Default arguments are evaluated once, when the `def` statement runs, so a mutable default is
> shared by every call — you can see it by printing the function's `__defaults__`. In a service
> that is state leaking between requests. The fix is a `None` sentinel, or a private sentinel
> object when `None` is a legal value; dataclasses and Pydantic catch it for you at class-creation
> time. Closures are late-binding: a lambda built in a loop captures the variable, not its value,
> so they all see the final value — I bind with a default argument or `functools.partial`. `is` is
> identity and `==` is value; small integers and compile-time string literals are cached, which
> makes `is` accidentally work and teaches people the wrong lesson, so I only use `is` for `None`,
> the booleans, and sentinels. And copies are shallow by default — `dict.copy()` gives you a new
> outer dict sharing the same nested values, which is why nested config appears to change
> underneath you.
