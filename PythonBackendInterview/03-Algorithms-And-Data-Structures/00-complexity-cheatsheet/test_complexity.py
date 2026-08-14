"""Asserts the complexity CLAIMS behave as claimed, rather than trusting the table.

Timing tests are inherently noisy, so these assert order-of-magnitude relationships with wide
margins -- enough to catch "this is a different complexity class", not to measure constants.
"""

from __future__ import annotations

import timeit
from collections import OrderedDict, deque

import pytest

pytestmark = pytest.mark.slow


def _per_op(stmt: str, setup: str, number: int) -> float:
    return timeit.timeit(stmt, setup=setup, number=number) / number


def test_list_membership_grows_with_n_but_set_does_not() -> None:
    small = _per_op("t in d", "d = list(range(1000)); t = 999", 500)
    large = _per_op("t in d", "d = list(range(100000)); t = 99999", 500)
    assert large / small > 20, f"list membership should scale with n (got {large / small:.1f}x)"

    small_set = _per_op("t in d", "d = set(range(1000)); t = 999", 20000)
    large_set = _per_op("t in d", "d = set(range(100000)); t = 99999", 20000)
    assert large_set / small_set < 5, (
        f"set membership should be flat (got {large_set / small_set:.1f}x)"
    )


def test_set_membership_beats_list_membership_dramatically() -> None:
    """The practical fix: one `set(...)` call changes the complexity class."""
    setup = (
        "import random; random.seed(1)\n"
        "items = [random.randrange(50000) for _ in range(3000)]\n"
        "allowed = list(range(25000))"
    )
    slow = _per_op("[i for i in items if i in allowed]", setup, 3)
    fast = _per_op("a = set(allowed)\n[i for i in items if i in a]", setup, 3)
    assert slow / fast > 20, f"expected a large speedup, got {slow / fast:.1f}x"


def test_deque_popleft_is_flat_and_list_pop_zero_is_not() -> None:
    small = _per_op("d.pop(0)", "d = list(range(10000))", 2000)
    large = _per_op("d.pop(0)", "d = list(range(100000))", 2000)
    assert large / small > 3, f"list.pop(0) should scale with n (got {large / small:.1f}x)"

    dq_small = _per_op(
        "d.popleft()", "from collections import deque; d = deque(range(10000))", 2000
    )
    dq_large = _per_op(
        "d.popleft()", "from collections import deque; d = deque(range(100000))", 2000
    )
    assert dq_large / dq_small < 3, "deque.popleft should be O(1)"


def test_join_beats_repeated_concatenation() -> None:
    setup = "parts = ['abcdefgh'] * 8000"
    concat = _per_op("out = ''\nfor s in parts: out += s", setup, 20)
    joined = _per_op("''.join(parts)", setup, 20)
    assert concat / joined > 3, f"join should win clearly, got {concat / joined:.1f}x"


def test_nlargest_beats_full_sort_for_small_k() -> None:
    setup = "import heapq, random; random.seed(1); d=[random.random() for _ in range(100000)]"
    full = _per_op("sorted(d, reverse=True)[:10]", setup, 10)
    heap = _per_op("heapq.nlargest(10, d)", setup, 10)
    assert full > heap, f"nlargest should win for k<<n (sort {full:.4f}s vs heap {heap:.4f}s)"


def test_slicing_copies_rather_than_viewing() -> None:
    original = [1, 2, 3]
    copy = original[:]
    assert copy is not original
    copy.append(4)
    assert original == [1, 2, 3]


def test_timsort_is_stable() -> None:
    """Stability is a guarantee you can rely on -- sort by secondary key first, then primary."""
    records = [("b", 2), ("a", 1), ("c", 2), ("d", 1)]
    assert sorted(records, key=lambda r: r[1]) == [("a", 1), ("d", 1), ("b", 2), ("c", 2)]


def test_dict_preserves_insertion_order_but_lacks_move_to_end() -> None:
    d = {"first": 1, "second": 2, "third": 3}
    assert list(d) == ["first", "second", "third"]
    assert not hasattr(d, "move_to_end")
    assert hasattr(OrderedDict(), "move_to_end"), "which is why an LRU uses OrderedDict"


def test_heapq_is_a_min_heap() -> None:
    """The most common heapq mistake: expecting a max-heap."""
    import heapq

    data = [5, 1, 9, 3]
    heapq.heapify(data)
    assert heapq.heappop(data) == 1, "heapq pops the SMALLEST"

    negated = [-x for x in [5, 1, 9, 3]]
    heapq.heapify(negated)
    assert -heapq.heappop(negated) == 9, "negate to get max-heap behaviour"


def test_heap_of_tuples_needs_a_tiebreaker() -> None:
    """Without one, equal priorities force Python to compare the payloads."""
    import heapq

    class Task:
        pass

    heap: list = []
    heapq.heappush(heap, (1, Task()))
    with pytest.raises(TypeError):
        heapq.heappush(heap, (1, Task()))  # equal priority -> compares Task objects

    tiebroken: list = []
    heapq.heappush(tiebroken, (1, 0, Task()))
    heapq.heappush(tiebroken, (1, 1, Task()))  # fine
    assert len(tiebroken) == 2


def test_groupby_requires_sorted_input() -> None:
    """The classic itertools trap: it groups CONSECUTIVE equal keys only."""
    from itertools import groupby

    unsorted = ["a", "b", "a"]
    fragmented = {k: len(list(g)) for k, g in groupby(sorted(unsorted))}
    assert fragmented == {"a": 2, "b": 1}

    groups = [(k, len(list(g))) for k, g in groupby(unsorted)]
    assert groups == [("a", 1), ("b", 1), ("a", 1)], "unsorted input fragments the groups"


def test_defaultdict_creates_on_read() -> None:
    """A real gotcha: merely LOOKING at a missing key inserts it."""
    from collections import defaultdict

    d: defaultdict[str, list] = defaultdict(list)
    _ = d["never-set"]
    assert "never-set" in d, "reading a missing key created it"
    assert len(d) == 1


def test_counter_arithmetic() -> None:
    from collections import Counter

    a, b = Counter("aab"), Counter("abc")
    assert (a - b) == Counter({"a": 1}), "subtraction drops non-positive counts"
    assert (a & b) == Counter({"a": 1, "b": 1}), "intersection takes the minimum"
    assert a.most_common(1) == [("a", 2)]


def test_deque_maxlen_is_a_ring_buffer() -> None:
    window = deque(maxlen=3)
    for i in range(5):
        window.append(i)
    assert list(window) == [2, 3, 4], "oldest entries are dropped automatically"
