"""Proves the claims in the README rather than asserting them in prose.

These tests are timing-based by nature, so the thresholds are deliberately loose -- they need to
separate "the loop was completely frozen" from "the loop kept running", not measure precisely.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from blocking_the_loop import Heartbeat, blocking_io, cpu_bound

pytestmark = pytest.mark.slow

TICK = 0.005
WORK = 0.15


async def _ticks_during(body) -> int:  # noqa: ANN001
    async with Heartbeat(interval=TICK) as hb:
        await body()
    return hb.ticks


async def test_time_sleep_in_a_coroutine_freezes_the_loop() -> None:
    """The bug: a coroutine that never awaits never yields, so nothing else runs."""

    async def blocking() -> None:
        blocking_io_short()

    ticks = await _ticks_during(blocking)
    assert ticks <= 1, f"expected the loop to be frozen, but it ticked {ticks} times"


async def test_cpu_bound_work_also_freezes_the_loop() -> None:
    async def burning() -> None:
        cpu_bound_short()

    ticks = await _ticks_during(burning)
    assert ticks <= 1, f"expected the loop to be frozen, but it ticked {ticks} times"


async def test_to_thread_keeps_the_loop_responsive() -> None:
    """The fix for blocking I/O: the wait happens on a worker thread, which releases the GIL."""

    async def offloaded() -> None:
        await asyncio.to_thread(blocking_io_short)

    ticks = await _ticks_during(offloaded)
    expected = WORK / TICK
    assert ticks >= expected * 0.5, f"loop should have kept ticking, got {ticks}/{expected:.0f}"


async def test_asyncio_sleep_keeps_the_loop_responsive() -> None:
    """`asyncio.sleep` yields to the loop; `time.sleep` holds the thread. This is the pair
    of names most often confused, and the distinction is the whole topic."""

    async def native() -> None:
        await asyncio.sleep(WORK)

    ticks = await _ticks_during(native)
    expected = WORK / TICK
    assert ticks >= expected * 0.5


async def test_gather_does_not_rescue_a_blocking_call() -> None:
    """A trap worth internalising: `gather` gives you concurrency only if the coroutines
    actually yield. Three blocking calls under `gather` run strictly one after another, so the
    total time is the SUM, not the max."""

    async def blocking() -> None:
        blocking_io_short()

    started = time.perf_counter()
    await asyncio.gather(blocking(), blocking(), blocking())
    elapsed = time.perf_counter() - started

    assert elapsed >= WORK * 2.5, (
        f"blocking calls under gather must serialise (expected ~{WORK * 3:.2f}s, got {elapsed:.2f}s)"
    )


async def test_to_thread_under_gather_really_is_concurrent() -> None:
    """The same three calls, offloaded, overlap: total is close to one call, not three."""
    started = time.perf_counter()
    await asyncio.gather(
        asyncio.to_thread(blocking_io_short),
        asyncio.to_thread(blocking_io_short),
        asyncio.to_thread(blocking_io_short),
    )
    elapsed = time.perf_counter() - started

    assert elapsed < WORK * 2, f"threads should overlap, took {elapsed:.2f}s"


# Short-duration stand-ins so the suite stays quick.


def blocking_io_short() -> None:
    time.sleep(WORK)


def cpu_bound_short() -> int:
    deadline = time.perf_counter() + WORK
    total = 0
    while time.perf_counter() < deadline:
        total += sum(i * i for i in range(1000))
    return total
