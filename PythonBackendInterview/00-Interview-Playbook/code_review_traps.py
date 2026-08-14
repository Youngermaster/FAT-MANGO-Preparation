"""Fifteen snippets with seeded bugs -- the "what's wrong with this code?" round.

    uv run python 00-Interview-Playbook/code_review_traps.py

How to use this file: read ONLY the `broken_*` function and say what is wrong out loud. Then read
the `WHY` comment and the `fixed_*` version. Cover the bottom half of your screen.

`test_code_review_traps.py` proves every bug is real and every fix works -- so none of these are
"bugs" that only exist in prose.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator


# ==========================================================================================
# 1. Silent failure after retries
# ==========================================================================================
def broken_fetch_with_retry(fetch, attempts=3):  # noqa: ANN001
    for _ in range(attempts):
        try:
            return fetch()
        except Exception:
            time.sleep(0.001)


# WHY: when every attempt fails the loop ends and the function returns None. The caller cannot
# tell "the API returned null" from "we gave up". A loud error became silent bad data.
def fixed_fetch_with_retry(fetch, attempts=3):  # noqa: ANN001
    for attempt in range(attempts):
        try:
            return fetch()
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(0.001)
    raise AssertionError("unreachable")


# ==========================================================================================
# 2. Blocking call inside a coroutine
# ==========================================================================================
async def broken_handler() -> str:
    time.sleep(0.05)
    return "done"


# WHY: `async def` runs on the event loop and `time.sleep` never yields, so the WHOLE server
# freezes -- every other request, the health check, background tasks. Use `asyncio.sleep` for
# real async work, or `asyncio.to_thread` for a blocking library you cannot replace.
async def fixed_handler() -> str:
    await asyncio.sleep(0.05)
    return "done"


# ==========================================================================================
# 3. Mutable default argument
# ==========================================================================================
def broken_add_tag(tag, tags=[]):  # noqa: B006, ANN001
    tags.append(tag)
    return tags


# WHY: the default is created once, at def time, and shared by every call. In a service that is
# state leaking between requests.
def fixed_add_tag(tag, tags=None):  # noqa: ANN001
    if tags is None:
        tags = []
    tags.append(tag)
    return tags


# ==========================================================================================
# 4. Late-binding closure
# ==========================================================================================
def broken_make_handlers():
    return [lambda: f"handler-{i}" for i in range(3)]  # noqa: B023


# WHY: all three close over the same variable, which is 2 by the time any of them runs.
def fixed_make_handlers():
    return [lambda i=i: f"handler-{i}" for i in range(3)]


# ==========================================================================================
# 5. Catching BaseException / swallowing CancelledError
# ==========================================================================================
async def broken_worker(log: list[str]) -> None:
    try:
        await asyncio.sleep(10)
    except BaseException:  # noqa: BLE001
        log.append("swallowed")


# WHY: `CancelledError` inherits from BaseException (since 3.8). Catching BaseException without
# re-raising makes the task UNCANCELLABLE -- graceful shutdown hangs, timeouts do not fire.
# Catch it if you need cleanup, then ALWAYS re-raise.
async def fixed_worker(log: list[str]) -> None:
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        log.append("cleaning up")
        raise


# ==========================================================================================
# 6. Truthiness instead of `is None`
# ==========================================================================================
def broken_page_size(limit=None):  # noqa: ANN001
    return limit or 50


# WHY: `limit=0` is falsy, so an explicit 0 silently becomes 50. Same bug for "", [], and False.
def fixed_page_size(limit=None):  # noqa: ANN001
    return 50 if limit is None else limit


# ==========================================================================================
# 7. Reading a whole file into memory
# ==========================================================================================
def broken_count_errors(path: str) -> int:
    with open(path) as fh:
        lines = fh.readlines()
    return len([line for line in lines if "ERROR" in line])


# WHY: `readlines()` materialises the entire file. On a multi-GB log that is an OOM kill. A file
# object is already a lazy iterator of lines -- stream it.
def fixed_count_errors(path: str) -> int:
    with open(path) as fh:
        return sum(1 for line in fh if "ERROR" in line)


# ==========================================================================================
# 8. String concatenation in a loop
# ==========================================================================================
def broken_join(items: list[str]) -> str:
    out = ""
    for item in items:
        out += item + ","
    return out.rstrip(",")


# WHY: strings are immutable, so each `+=` builds a new string and copies everything so far --
# O(n^2). `str.join` allocates once.
def fixed_join(items: list[str]) -> str:
    return ",".join(items)


# ==========================================================================================
# 9. Membership test against a list
# ==========================================================================================
def broken_filter_allowed(items: list[int], allowed: list[int]) -> list[int]:
    return [i for i in items if i in allowed]


# WHY: `in` on a list is O(n), making this O(n*m). A set gives O(1) membership -> O(n+m).
def fixed_filter_allowed(items: list[int], allowed: list[int]) -> list[int]:
    allowed_set = set(allowed)
    return [i for i in items if i in allowed_set]


# ==========================================================================================
# 10. Mutating a collection while iterating it
# ==========================================================================================
def broken_drop_negatives(values: list[int]) -> list[int]:
    for value in values:
        if value < 0:
            values.remove(value)
    return values


# WHY: removing shifts every later element left while the iterator's index keeps advancing, so
# elements get SKIPPED. Two adjacent negatives and one survives. Build a new list instead.
def fixed_drop_negatives(values: list[int]) -> list[int]:
    return [v for v in values if v >= 0]


# ==========================================================================================
# 11. A generator where the caller expects a list
# ==========================================================================================
def broken_get_ids(rows: list[dict]) -> Iterator[int]:
    return (row["id"] for row in rows)


# WHY: a generator is single-use and lazy. `len()` fails, a second iteration yields nothing, and
# if it reads a file the file may be closed by the time it runs. Fine as an internal pipeline;
# a landmine when returned from a public API that promises a sequence.
def fixed_get_ids(rows: list[dict]) -> list[int]:
    return [row["id"] for row in rows]


# ==========================================================================================
# 12. Except that hides the error
# ==========================================================================================
def broken_parse_port(raw: str) -> int:
    try:
        return int(raw)
    except Exception:  # noqa: BLE001
        return 8080


# WHY: a typo in config silently becomes the default and the service listens on the wrong port,
# with nothing in the logs. Catch the SPECIFIC exception and at minimum log it -- better, fail
# fast: bad configuration should stop the process, not be papered over.
def fixed_parse_port(raw: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"invalid port {raw!r}") from exc


# ==========================================================================================
# 13. Unbounded fan-out
# ==========================================================================================
async def broken_fetch_all(urls: list[str], fetch):  # noqa: ANN001
    return await asyncio.gather(*(fetch(u) for u in urls))


# WHY: with 10,000 URLs this opens 10,000 connections at once -- exhausts the connection pool,
# hits the file-descriptor limit, and DDoSes the dependency. Bound it with a semaphore.
async def fixed_fetch_all(urls: list[str], fetch, limit: int = 10):  # noqa: ANN001
    semaphore = asyncio.Semaphore(limit)

    async def bounded(url: str):
        async with semaphore:
            return await fetch(url)

    return await asyncio.gather(*(bounded(u) for u in urls))


# ==========================================================================================
# 14. Decorator that loses the function's identity
# ==========================================================================================
def broken_timed(func):  # noqa: ANN001
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


# WHY: no `functools.wraps`, so `__name__` becomes "wrapper", the docstring is gone, and the
# signature is (*args, **kwargs). That breaks introspection, API docs, and anything that reads
# type hints off the function -- FastAPI could not build a route from it.
def fixed_timed(func):  # noqa: ANN001
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


# ==========================================================================================
# 15. Resource not closed on the error path
# ==========================================================================================
def broken_read_config(path: str) -> str:
    fh = open(path)
    data = fh.read()
    validate_not_empty(data)  # may raise -- and then the file is never closed
    fh.close()
    return data


# WHY: any exception between open and close leaks the descriptor. In a long-running service that
# accumulates until "too many open files". `with` closes on every path.
def fixed_read_config(path: str) -> str:
    with open(path) as fh:
        data = fh.read()
    validate_not_empty(data)
    return data


def validate_not_empty(data: str) -> None:
    if not data.strip():
        raise ValueError("config is empty")


TRAPS = [
    (1, "returns None after exhausting retries"),
    (2, "blocking call freezes the event loop"),
    (3, "mutable default argument shared across calls"),
    (4, "late-binding closure captures the variable"),
    (5, "catching BaseException swallows CancelledError"),
    (6, "`or` treats a legitimate 0 as missing"),
    (7, "readlines() loads the whole file"),
    (8, "string += in a loop is O(n^2)"),
    (9, "`in` on a list is O(n)"),
    (10, "mutating a list while iterating skips elements"),
    (11, "returning a single-use generator as if it were a list"),
    (12, "bare except hides a config error"),
    (13, "unbounded gather over N urls"),
    (14, "decorator without functools.wraps"),
    (15, "file not closed when validation raises"),
]


if __name__ == "__main__":
    print("\nFifteen seeded bugs. Say what is wrong before reading the WHY comment.\n")
    for number, summary in TRAPS:
        print(f"  {number:>2}. {summary}")
    print(
        "\nEach one is proven by test_code_review_traps.py -- run:"
        "\n    uv run pytest 00-Interview-Playbook\n"
    )

    # A couple of the differences are worth seeing rather than reading.
    print("  #3  broken_add_tag('a'), then ('b') ->", broken_add_tag("a"), broken_add_tag("b"))
    print("  #4  broken handlers ->", [h() for h in broken_make_handlers()])
    print("  #6  broken_page_size(0) ->", broken_page_size(0), "(expected 0)")
    print("  #10 broken_drop_negatives([-1, -2, 3]) ->", broken_drop_negatives([-1, -2, 3]))
    print("  #14 broken_timed(f).__name__ ->", broken_timed(validate_not_empty).__name__)
    print()
