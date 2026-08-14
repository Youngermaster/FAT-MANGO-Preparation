"""The limit must actually hold, order must be preserved, and nothing may leak."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from concurrency_limits import (
    ConcurrencyTracker,
    imap_unordered,
    map_with_semaphore,
    map_with_taskgroup,
    map_with_worker_pool,
)

ORDERED_RUNNERS = [map_with_semaphore, map_with_worker_pool, map_with_taskgroup]
_ids = [r.__name__ for r in ORDERED_RUNNERS]


def _tracked_job(tracker: ConcurrencyTracker, delay: float = 0.01):
    async def job(item: int) -> int:
        tracker.enter()
        try:
            await asyncio.sleep(delay)
            return item * 2
        finally:
            tracker.exit()

    return job


@pytest.mark.parametrize("runner", ORDERED_RUNNERS, ids=_ids)
async def test_never_exceeds_the_limit(runner: Any) -> None:
    tracker = ConcurrencyTracker()
    await runner(_tracked_job(tracker), list(range(50)), limit=4)
    assert tracker.peak <= 4, f"{runner.__name__} let {tracker.peak} run at once"


@pytest.mark.parametrize("runner", ORDERED_RUNNERS, ids=_ids)
async def test_actually_reaches_the_limit(runner: Any) -> None:
    """A limit of 4 that only ever runs 1 at a time would 'pass' the test above.

    This is the mistake of acquiring the semaphore *around* the gather instead of inside the
    worker: correct-looking, and completely serial.
    """
    tracker = ConcurrencyTracker()
    await runner(_tracked_job(tracker), list(range(50)), limit=4)
    assert tracker.peak == 4, f"{runner.__name__} only reached {tracker.peak}; is it serialising?"


@pytest.mark.parametrize("runner", ORDERED_RUNNERS, ids=_ids)
async def test_preserves_input_order(runner: Any) -> None:
    """Completion order is not submission order, but results must line up with the input."""

    async def variable_delay(item: int) -> int:
        # Later items finish sooner, so any order-preserving bug shows up immediately.
        await asyncio.sleep(0.02 - item * 0.0015)
        return item * 2

    results = await runner(variable_delay, list(range(10)), limit=3)
    assert list(results) == [i * 2 for i in range(10)]


@pytest.mark.parametrize("runner", ORDERED_RUNNERS, ids=_ids)
async def test_handles_empty_input(runner: Any) -> None:
    async def never_called(item: int) -> int:  # pragma: no cover
        raise AssertionError("should not be called")

    assert list(await runner(never_called, [], limit=5)) == []


@pytest.mark.parametrize("runner", ORDERED_RUNNERS, ids=_ids)
async def test_limit_larger_than_input_is_fine(runner: Any) -> None:
    tracker = ConcurrencyTracker()
    results = await runner(_tracked_job(tracker), list(range(3)), limit=100)
    assert list(results) == [0, 2, 4]
    assert tracker.peak == 3


async def test_semaphore_is_released_when_the_job_raises() -> None:
    """`async with semaphore` must release on the error path, or the pool deadlocks.

    If a failure leaked a permit, `limit` failures would exhaust the semaphore and every
    subsequent item would wait forever.
    """
    calls = 0

    async def always_fails(item: int) -> int:
        nonlocal calls
        calls += 1
        raise ValueError(f"item {item}")

    results = await map_with_semaphore(
        always_fails, list(range(20)), limit=3, return_exceptions=True
    )
    assert calls == 20, "every item must have been attempted; a leaked permit would hang"
    assert all(isinstance(r, ValueError) for r in results)


async def test_worker_pool_records_failures_per_item_without_hanging() -> None:
    """`task_done()` lives in a `finally`. Without that, `queue.join()` never returns."""

    async def fails_on_odds(item: int) -> int:
        if item % 2:
            raise ValueError(item)
        return item

    results = await asyncio.wait_for(
        map_with_worker_pool(fails_on_odds, list(range(10)), limit=3), timeout=5.0
    )
    assert [r for r in results if not isinstance(r, BaseException)] == [0, 2, 4, 6, 8]
    assert all(isinstance(results[i], ValueError) for i in range(1, 10, 2))


async def test_worker_pool_leaves_no_tasks_behind() -> None:
    """Workers loop forever, so they must be cancelled when the function returns."""
    before = len(asyncio.all_tasks())

    async def job(item: int) -> int:
        await asyncio.sleep(0.001)
        return item

    await map_with_worker_pool(job, list(range(20)), limit=5)
    await asyncio.sleep(0)  # let cancellations settle

    assert len(asyncio.all_tasks()) <= before, "worker tasks leaked"


async def test_taskgroup_variant_cancels_siblings_on_failure() -> None:
    started: list[int] = []

    async def one_bad_apple(item: int) -> int:
        started.append(item)
        if item == 0:
            raise ValueError("bad")
        await asyncio.sleep(1.0)
        return item

    with pytest.raises(BaseExceptionGroup):
        await map_with_taskgroup(one_bad_apple, list(range(20)), limit=4)

    # If siblings were not cancelled this would have taken a second.
    assert len(started) < 20


async def test_imap_unordered_yields_in_completion_order() -> None:
    async def variable_delay(item: int) -> int:
        await asyncio.sleep(0.05 - item * 0.008)
        return item

    got = [r async for r in imap_unordered(variable_delay, list(range(5)), limit=5)]
    assert got == sorted(got, reverse=True), "later items finish first, so we expect 4,3,2,1,0"
    assert sorted(got) == [0, 1, 2, 3, 4]


async def test_imap_unordered_cancels_the_rest_on_early_break() -> None:
    finished: list[int] = []

    async def job(item: int) -> int:
        await asyncio.sleep(0.01 * item)
        finished.append(item)
        return item

    async for _ in imap_unordered(job, list(range(20)), limit=20):
        break  # consumer stops after the first result

    await asyncio.sleep(0.15)
    assert len(finished) < 20, "abandoning the generator must cancel the outstanding work"


async def test_unbounded_gather_really_is_unbounded() -> None:
    """The motivation for all of the above."""
    tracker = ConcurrencyTracker()
    job = _tracked_job(tracker, delay=0.02)
    await asyncio.gather(*(job(i) for i in range(100)))
    assert tracker.peak == 100
