"""Big-O of Python builtins -- measured, not recited.

    uv run python 03-Algorithms-And-Data-Structures/00-complexity-cheatsheet/complexity.py

Knowing that `x in list` is O(n) is worth little; being able to say "I measured it and it is 200x
slower at n=20,000" is worth a lot. Every number this file prints is timed on the machine you run
it on.

The point is not the exact numbers -- it is the SHAPE. Doubling n and watching the time double
(linear), quadruple (quadratic), or barely move (constant) is what makes the table stick.
"""

from __future__ import annotations

import timeit


def _time(stmt: str, setup: str, number: int = 1000) -> float:
    """Seconds per operation."""
    total = timeit.timeit(stmt, setup=setup, number=number)
    return total / number


def _scaling(label: str, stmt: str, setup_template: str, sizes: list[int], number: int) -> None:
    """Print time at each n, plus the ratio, which is what reveals the complexity class."""
    times = [_time(stmt, setup_template.format(n=n), number=number) for n in sizes]
    cells = "  ".join(f"{t * 1e6:>9.2f}" for t in times)
    ratios = "  ".join(f"{times[i + 1] / times[i]:>5.1f}x" for i in range(len(times) - 1))
    print(f"  {label:<34} {cells}   |  {ratios}")


def membership() -> None:
    print("\nMEMBERSHIP: `x in list` vs `x in set`   (microseconds per lookup)")
    print(f"  {'':34} {'n=1k':>9}  {'n=10k':>9}  {'n=100k':>9}   |  growth")
    sizes = [1_000, 10_000, 100_000]

    _scaling(
        "x in list      -> O(n)",
        "target in data",
        "data = list(range({n})); target = {n} - 1",
        sizes,
        number=200,
    )
    _scaling(
        "x in set       -> O(1)",
        "target in data",
        "data = set(range({n})); target = {n} - 1",
        sizes,
        number=20000,
    )
    _scaling(
        "x in dict      -> O(1)",
        "target in data",
        "data = {{i: 1 for i in range({n})}}; target = {n} - 1",
        sizes,
        number=20000,
    )
    print("\n  The list column roughly 10x per 10x of n; set and dict barely move.")
    print("  This is THE most common accidental O(n*m): a membership test inside a loop.")


def front_operations() -> None:
    print("\nFRONT OF SEQUENCE: `list.pop(0)` vs `deque.popleft()`")
    print(f"  {'':34} {'n=10k':>9}  {'n=100k':>9}   |  growth")
    sizes = [10_000, 100_000]

    _scaling("list.pop(0)    -> O(n)", "data.pop(0)", "data = list(range({n}))", sizes, number=2000)
    _scaling(
        "deque.popleft()-> O(1)",
        "data.popleft()",
        "from collections import deque; data = deque(range({n}))",
        sizes,
        number=2000,
    )
    print("\n  Every list.pop(0) shifts every remaining element left. A BFS written with a list")
    print("  as the queue is quietly O(n^2) -- use collections.deque.")


def string_building() -> None:
    print("\nSTRING BUILDING: `+=` in a loop vs `str.join`")
    print(f"  {'':34} {'n=2k':>9}  {'n=8k':>9}   |  growth")
    sizes = [2_000, 8_000]

    _scaling(
        "out += s       -> O(n^2)",
        "out = ''\nfor s in parts: out += s",
        "parts = ['abcdefgh'] * {n}",
        sizes,
        number=20,
    )
    _scaling(
        "''.join(parts) -> O(n)", "''.join(parts)", "parts = ['abcdefgh'] * {n}", sizes, number=20
    )
    print("\n  Strings are immutable, so `+=` should allocate a new string and copy everything")
    print("  so far -- O(n^2), i.e. 4x the input should cost ~16x the time.")
    print("\n  LOOK AT THE MEASURED GROWTH: it is closer to 4x, not 16x. CPython has an")
    print("  in-place realloc optimisation that applies when the target string has a")
    print("  refcount of 1, so this loop often behaves linearly -- just with a much larger")
    print("  constant (join is still ~10x faster here).")
    print("\n  That is the interesting version of this answer. The optimisation is a CPython")
    print("  implementation detail: it does not apply on PyPy, and it silently stops applying")
    print("  as soon as anything else holds a reference to the string. So `+=` in a loop is a")
    print("  latent O(n^2) that passes review, benchmarks fine, and degrades later. Use join.")


def top_k() -> None:
    print("\nTOP-K: full sort vs heapq.nlargest   (k=10)")
    print(f"  {'':34} {'n=10k':>9}  {'n=100k':>9}   |  growth")
    sizes = [10_000, 100_000]

    _scaling(
        "sorted(xs)[:10]-> O(n log n)",
        "sorted(data, reverse=True)[:10]",
        "import random; random.seed(1); data=[random.random() for _ in range({n})]",
        sizes,
        number=20,
    )
    _scaling(
        "nlargest(10,xs)-> O(n log k)",
        "heapq.nlargest(10, data)",
        "import heapq, random; random.seed(1); data=[random.random() for _ in range({n})]",
        sizes,
        number=20,
    )
    print("\n  When k is much smaller than n, a heap avoids ordering the 99.99% you discard.")


def slicing() -> None:
    print("\nSLICING COPIES: a[:] is O(n), not a view")
    for n in (10_000, 100_000):
        t = _time("data[:]", f"data = list(range({n}))", number=2000)
        print(f"  copy a list of {n:>7,} elements     {t * 1e6:>9.2f} us")
    print("\n  `a[1:]` inside a recursive function turns an O(n) algorithm into O(n^2).")
    print("  Pass indices instead, or use memoryview for bytes.")


def sorting_is_stable() -> None:
    print("\nSTABILITY: Timsort keeps the order of equal keys")
    records = [("b", 2), ("a", 1), ("c", 2), ("d", 1)]
    by_value = sorted(records, key=lambda r: r[1])
    print(f"  input           {records}")
    print(f"  sorted by value {by_value}")
    print("  'a' still precedes 'd', and 'b' precedes 'c' -- so you can sort by a secondary key")
    print("  first, then by the primary one, and the secondary ordering survives.")


def dict_ordering() -> None:
    print("\nDICT ORDERING is guaranteed (3.7+), but a dict is not an OrderedDict")
    d = {"first": 1, "second": 2, "third": 3}
    print(f"  insertion order preserved: {list(d)}")
    print(
        f"  has move_to_end? dict={hasattr(d, 'move_to_end')} "
        f"OrderedDict={hasattr(__import__('collections').OrderedDict(), 'move_to_end')}"
    )
    print("  That missing method is exactly why an LRU cache uses OrderedDict.")


def practical_lesson() -> None:
    """The one-line fix that matters most in real code."""
    print("\nTHE PRACTICAL VERSION: filtering one list against another")
    setup = (
        "import random; random.seed(1)\n"
        "items = [random.randrange(50000) for _ in range(5000)]\n"
        "allowed = list(range(25000))"
    )
    slow = _time("[i for i in items if i in allowed]", setup, number=3)
    fast = _time("aset = set(allowed)\n[i for i in items if i in aset]", setup, number=3)
    print(f"  membership against a list   {slow * 1e3:>8.2f} ms")
    print(f"  membership against a set    {fast * 1e3:>8.2f} ms   ({slow / fast:.0f}x faster)")
    print("  One line -- `allowed = set(allowed)` -- and it is a different complexity class.")


def main() -> None:
    print("\n" + "=" * 86)
    print("  Big-O of Python builtins, measured on this machine")
    print("=" * 86)
    membership()
    front_operations()
    string_building()
    top_k()
    slicing()
    sorting_is_stable()
    dict_ordering()
    practical_lesson()
    print("\n  Read the growth column, not the absolute numbers.\n")


if __name__ == "__main__":
    main()
