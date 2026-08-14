"""Fan out to N items with at most K running at once -- the canonical async live-coding task.

    uv run python 02-Async-And-Concurrency/06-semaphores-and-concurrency-limits/concurrency_limits.py

Prompt as you will hear it: "Fetch 1000 URLs, but never more than 10 at a time."

Four implementations, in the order you should reach for them. Each tracks peak concurrency so
you can see the limit actually holding rather than take it on faith.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class ConcurrencyTracker:
    """Records how many workers were in flight simultaneously."""

    current: int = 0
    peak: int = 0

    def enter(self) -> None:
        self.current += 1
        self.peak = max(self.peak, self.current)

    def exit(self) -> None:
        self.current -= 1


# ==========================================================================================
# 1. Semaphore + gather -- the answer to give first
# ==========================================================================================


async def map_with_semaphore(
    func: Callable[[T], Awaitable[R]],
    items: Sequence[T],
    *,
    limit: int = 10,
    return_exceptions: bool = False,
) -> list[R]:
    """Run `func` over every item, at most `limit` concurrently. Results keep input order.

    The semaphore is acquired INSIDE the worker, not around the gather. That ordering is the
    whole trick: all N tasks are created immediately, but each one blocks on `acquire()` until
    a slot frees. Wrapping the gather instead would serialise everything.

    Caveat to state out loud: this still creates N Task objects up front. For a thousand URLs
    that is fine; for ten million it is not, and you want the queue-based worker pool below.
    """
    semaphore = asyncio.Semaphore(limit)

    async def bounded(item: T) -> R:
        async with semaphore:  # acquire, and release even if func raises
            return await func(item)

    return await asyncio.gather(
        *(bounded(item) for item in items), return_exceptions=return_exceptions
    )  # type: ignore[return-value]


# ==========================================================================================
# 2. Worker pool over a queue -- the answer for unbounded/streaming input
# ==========================================================================================


async def map_with_worker_pool(
    func: Callable[[T], Awaitable[R]],
    items: Iterable[T],
    *,
    limit: int = 10,
) -> list[R | BaseException]:
    """Same contract, but only `limit` tasks exist at any time regardless of input size.

    This is the version to reach for when the input is a stream, a paginated API, or a file with
    ten million lines. The queue's `maxsize` provides backpressure: the producer cannot run
    arbitrarily far ahead of the consumers and blow up memory.

    Results are collected into a pre-sized list by index so input order is preserved even though
    completion order is not.
    """
    queue: asyncio.Queue[tuple[int, T]] = asyncio.Queue(maxsize=limit * 2)
    materialised = list(items)
    results: list[Any] = [None] * len(materialised)

    async def worker() -> None:
        while True:
            index, item = await queue.get()
            try:
                results[index] = await func(item)
            except Exception as exc:  # noqa: BLE001 - recorded per item, not swallowed
                results[index] = exc
            finally:
                # MUST be in `finally`: `queue.join()` below waits for one `task_done()` per
                # item, so an exception that skipped it would hang the whole function forever.
                queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(limit)]
    try:
        for index, item in enumerate(materialised):
            await queue.put((index, item))  # blocks once the queue is full -> backpressure
        await queue.join()  # wait until every item has been marked done
    finally:
        # Workers loop forever, so they must be cancelled explicitly. Without this the function
        # returns while `limit` tasks linger, and the process never exits cleanly.
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    return results


# ==========================================================================================
# 3. Streaming results as they finish -- when you can act on each one immediately
# ==========================================================================================


async def imap_unordered(
    func: Callable[[T], Awaitable[R]],
    items: Sequence[T],
    *,
    limit: int = 10,
):
    """Async generator yielding results as they complete, still bounded by `limit`.

    Use when each result can be handled immediately -- streamed to the client, written to a
    database, pushed to a queue -- so you never hold all N results in memory at once.
    """
    semaphore = asyncio.Semaphore(limit)

    async def bounded(item: T) -> R:
        async with semaphore:
            return await func(item)

    tasks = [asyncio.create_task(bounded(item)) for item in items]
    try:
        for completed in asyncio.as_completed(tasks):
            yield await completed
    finally:
        # If the consumer stops early (a `break`, or the client disconnects), cancel the rest.
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


# ==========================================================================================
# 4. TaskGroup + semaphore -- structured, and the one to prefer on 3.11+
# ==========================================================================================


async def map_with_taskgroup(
    func: Callable[[T], Awaitable[R]],
    items: Sequence[T],
    *,
    limit: int = 10,
) -> list[R]:
    """Bounded fan-out with structured concurrency.

    Difference from the gather version: if one item fails, every other in-flight task is
    cancelled and you get an ExceptionGroup. That is usually what you want for an all-or-nothing
    operation, and usually NOT what you want for best-effort fan-out.
    """
    semaphore = asyncio.Semaphore(limit)

    async def bounded(item: T) -> R:
        async with semaphore:
            return await func(item)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(bounded(item)) for item in items]
    return [t.result() for t in tasks]


# ==========================================================================================
# Demo
# ==========================================================================================


async def main() -> None:
    rng = random.Random(20260814)
    delays = [rng.uniform(0.005, 0.02) for _ in range(40)]
    LIMIT = 5

    def make_job(tracker: ConcurrencyTracker):
        async def job(index: int) -> int:
            tracker.enter()
            try:
                await asyncio.sleep(delays[index])
                return index * 2
            finally:
                tracker.exit()

        return job

    print(f"\n40 jobs, limit={LIMIT}. 'peak' must never exceed the limit.\n")

    for label, runner in [
        ("semaphore + gather", map_with_semaphore),
        ("worker pool + queue", map_with_worker_pool),
        ("TaskGroup + semaphore", map_with_taskgroup),
    ]:
        tracker = ConcurrencyTracker()
        started = time.perf_counter()
        results = await runner(make_job(tracker), list(range(40)), limit=LIMIT)  # type: ignore[operator]
        elapsed = time.perf_counter() - started
        ordered = list(results) == [i * 2 for i in range(40)]
        print(f"  {label:<24} peak={tracker.peak}  {elapsed:.3f}s  order preserved: {ordered}")

    # Streaming variant: results arrive out of order, which is the point.
    tracker = ConcurrencyTracker()
    arrived: list[int] = []
    async for result in imap_unordered(make_job(tracker), list(range(40)), limit=LIMIT):
        arrived.append(result)
    print(
        f"  {'imap_unordered':<24} peak={tracker.peak}  "
        f"order preserved: {arrived == [i * 2 for i in range(40)]} (expected False)"
    )

    # --- Why the limit matters at all --------------------------------------------------
    print("\nUnbounded vs bounded, 200 jobs:")
    tracker = ConcurrencyTracker()
    await asyncio.gather(*(make_job(tracker)(i % 40) for i in range(200)))
    print(f"  unbounded gather  -> peak concurrency {tracker.peak} (all 200 at once)")

    tracker = ConcurrencyTracker()
    await map_with_semaphore(make_job(tracker), [i % 40 for i in range(200)], limit=LIMIT)
    print(f"  semaphore(limit={LIMIT})  -> peak concurrency {tracker.peak}")

    print(
        "\nUnbounded fan-out is how you DDoS your own dependency, exhaust the connection\n"
        "pool, and hit the file-descriptor limit -- all at once.\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
