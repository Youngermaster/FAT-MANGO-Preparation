"""The classic Python gotchas -- mutable defaults, late-binding closures, identity, copying.

    uv run python 01-Python-Core/02-mutability-and-gotchas/gotchas.py

Every one of these appears in the "what does this print?" round. They look like trivia, but each
one is a real bug that ships: the mutable default is a shared-state leak across requests, and the
late-binding closure is the bug in every for-loop that builds callbacks or handlers.

Nothing here is asserted from memory -- the file prints what actually happens, and
`test_gotchas.py` pins it.
"""

from __future__ import annotations

import copy
import sys
from dataclasses import dataclass, field

# ==========================================================================================
# 1. Mutable default arguments -- the single most-asked gotcha
# ==========================================================================================


def append_broken(item: int, target: list[int] = []) -> list[int]:  # noqa: B006
    """BUG. The default list is created ONCE, when the `def` statement executes.

    Every call that omits `target` shares the same list object, so it accumulates across calls.
    In a web service that is state leaking between requests -- and because it only shows up on
    the second call, it usually passes review and fails in production.
    """
    target.append(item)
    return target


def append_fixed(item: int, target: list[int] | None = None) -> list[int]:
    """The fix: `None` sentinel, build the real default inside the body.

    Why `None` rather than any other sentinel: it is unambiguous for most APIs. When `None` is a
    legitimate value the caller might pass, use a private module-level sentinel object instead
    (`_MISSING = object()`), which is what `functools` and `dataclasses` do internally.
    """
    if target is None:
        target = []
    target.append(item)
    return target


@dataclass
class ConfigBroken:
    """Dataclasses catch this at CLASS CREATION time -- a nice thing to know.

    Writing `tags: list[str] = []` here raises ValueError immediately rather than misbehaving
    later, which is why the field below uses `default_factory`.
    """

    tags: list[str] = field(default_factory=list)


# ==========================================================================================
# 2. Late-binding closures
# ==========================================================================================


def make_broken_callbacks() -> list:
    """BUG. Every lambda closes over the VARIABLE `i`, not its value at creation time.

    By the time any of them is called the loop has finished and `i` is 4, so all five return 4.
    This is the bug in every "build a list of handlers in a loop" -- event callbacks, retry
    partials, route handlers.

    Worth knowing for the interview: LINTERS CATCH THIS. Ruff's B023 (from flake8-bugbear) is
    exactly "function definition does not bind loop variable" -- which is why the line below
    needs an explicit `noqa` to survive `ruff check` in this repo. If asked how you would stop
    this class of bug reaching production, "bugbear catches it in CI" is a better answer than
    "I remember to look for it".
    """
    return [lambda: i for i in range(5)]  # noqa: B023


def make_fixed_callbacks_default_arg() -> list:
    """Fix 1: bind the value now via a default argument, which IS evaluated at def time.

    Slightly ugly, but it is the idiom you will see most often.
    """
    return [lambda i=i: i for i in range(5)]


def make_fixed_callbacks_partial() -> list:
    """Fix 2: `functools.partial` -- arguably clearer about the intent to bind."""
    from functools import partial

    def identity(value: int) -> int:
        return value

    return [partial(identity, i) for i in range(5)]


# ==========================================================================================
# 3. Identity vs equality
# ==========================================================================================


def identity_demo() -> list[str]:
    """`is` compares identity (same object); `==` compares value.

    The confusing part is CPython's caching, which makes `is` accidentally work sometimes:
      * small integers -5..256 are pre-created and shared
      * short string literals are interned at compile time

    The rule to state: use `is` ONLY for singletons -- None, True, False, and sentinel objects.
    Never for numbers or strings, no matter what you observed in the REPL.
    """
    out = []

    a, b = 256, 256
    out.append(f"256 is 256          -> {a is b}   (small-int cache)")

    c, d = 257, 257
    # Note: inside a single code block these may be folded to the same constant by the
    # compiler, so we build one at runtime to defeat that and show the real behaviour.
    e = int("257")
    out.append(f"257 is int('257')   -> {c is e}   (outside the cache)")
    out.append(f"257 == int('257')   -> {c == e}   (equality is what you meant)")
    del d

    s1 = "hello"
    s2 = "hel" + "lo"  # constant-folded at compile time
    s3 = "".join(["hel", "lo"])  # built at runtime
    out.append(f"'hello' is folded   -> {s1 is s2}   (compile-time interning)")
    out.append(f"'hello' is runtime  -> {s1 is s3}   (not interned)")
    out.append(f"'hello' == runtime  -> {s1 == s3}")

    return out


# ==========================================================================================
# 4. Shallow vs deep copy
# ==========================================================================================


def copy_demo() -> dict[str, object]:
    """Assignment, shallow copy and deep copy are three different things.

    A shallow copy duplicates the OUTER container and shares the inner objects. That is why
    mutating `shallow[0]` is visible through `original` -- the classic "why did my copy change"
    bug, and the reason `dict.copy()` is not enough for nested config.
    """
    original = [[1, 2], [3, 4]]

    alias = original  # same object
    shallow = copy.copy(original)  # new outer list, SAME inner lists
    deep = copy.deepcopy(original)  # new everything

    shallow[0].append(99)  # mutate an inner list through the shallow copy

    return {
        "original": original,
        "alias is original": alias is original,
        "shallow is original": shallow is original,
        "shallow[0] is original[0]": shallow[0] is original[0],
        "deep[0] is original[0]": deep[0] is original[0],
        "original changed via shallow": original[0] == [1, 2, 99],
        "deep unaffected": deep[0] == [1, 2],
    }


# ==========================================================================================
# 5. Class attributes are shared
# ==========================================================================================


class BrokenAccount:
    """BUG. `transactions` is a CLASS attribute, so every instance shares one list."""

    transactions: list[str] = []

    def add(self, item: str) -> None:
        self.transactions.append(item)  # mutates the shared class-level list


class FixedAccount:
    """Instance attribute, created per object in `__init__`."""

    def __init__(self) -> None:
        self.transactions: list[str] = []

    def add(self, item: str) -> None:
        self.transactions.append(item)


# ==========================================================================================
# 6. Truthiness vs `is None`
# ==========================================================================================


def truthiness_demo() -> list[str]:
    """`if not value:` and `if value is None:` are NOT the same test.

    Every one of these is falsy but not None. Confusing them is how a legitimate `0`, empty
    string or empty list gets silently replaced by a default -- a bug that is very hard to see
    in review because the code reads as if it says what you meant.
    """
    falsy = [0, 0.0, "", [], {}, set(), None, False]
    return [f"{v!r:<8} falsy={not v!s:<6} is None={v is None}" for v in falsy]


# ==========================================================================================
# 7. Integer caching is an implementation detail
# ==========================================================================================


def refcount_note() -> str:
    """A current detail worth knowing: `sys.getrefcount(1)` returns 2**32-1 on 3.12+.

    That is not "lots of references" -- it is the sentinel for an IMMORTAL object (PEP 683,
    Python 3.12). Certain objects (small ints, `None`, `True`/`False`, interned strings) are
    marked so their reference counts are never updated at all.

    Why it was done: refcount updates are writes, and writes to shared objects dirty CPU cache
    lines across cores. Skipping them for the hottest shared objects is a prerequisite for both
    per-interpreter GIL (PEP 684) and free-threaded Python (PEP 703) -- otherwise every thread
    touching `None` would be fighting over the same cache line.

    Mentioning this connects three topics at once: memory management, the GIL, and 3.13/3.14
    free-threading.
    """
    return (
        f"sys.getrefcount(1) = {sys.getrefcount(1)} -- the immortal-object sentinel "
        f"(PEP 683), not a real count"
    )


if __name__ == "__main__":
    print("\n1. MUTABLE DEFAULT ARGUMENT")
    print(f"   broken: {append_broken(1)}, {append_broken(2)}, {append_broken(3)}  <- accumulates!")
    print(f"   fixed:  {append_fixed(1)}, {append_fixed(2)}, {append_fixed(3)}")
    print(
        f"   why:    the default object is created once, at def time: {append_broken.__defaults__}"
    )

    print("\n2. LATE-BINDING CLOSURES")
    print(f"   broken:       {[f() for f in make_broken_callbacks()]}  <- all 4!")
    print(f"   default-arg:  {[f() for f in make_fixed_callbacks_default_arg()]}")
    print(f"   partial:      {[f() for f in make_fixed_callbacks_partial()]}")

    print("\n3. IDENTITY VS EQUALITY")
    for line in identity_demo():
        print(f"   {line}")

    print("\n4. SHALLOW VS DEEP COPY")
    for key, value in copy_demo().items():
        print(f"   {key:<28} {value}")

    print("\n5. CLASS VS INSTANCE ATTRIBUTES")
    a, b = BrokenAccount(), BrokenAccount()
    a.add("from a")
    print(f"   broken: b sees a's data -> {b.transactions}")
    c, d = FixedAccount(), FixedAccount()
    c.add("from c")
    print(f"   fixed:  d is independent -> {d.transactions}")

    print("\n6. FALSY IS NOT None")
    for line in truthiness_demo():
        print(f"   {line}")

    print(f"\n7. {refcount_note()}\n")
