"""The single most-asked async question: what happens when you block the event loop?

Run this file. It measures the damage rather than asserting it, because the number is what makes
the lesson stick:

    uv run python 02-Async-And-Concurrency/05-blocking-the-loop/blocking_the_loop.py

The scenario throughout: a "health check" coroutine ticks every 10 ms while some work happens
alongside it. A healthy event loop lets it tick. A blocked one does not -- and in a real service
those missed ticks are timed-out requests, failed liveness probes, and a pod being restarted.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class Heartbeat:
    """Ticks every `interval` seconds while running. A stand-in for 'every other request'."""

    interval: float = 0.01
    ticks: int = 0
    _task: asyncio.Task[None] | None = field(default=None, repr=False)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            self.ticks += 1

    async def __aenter__(self) -> Heartbeat:
        self.ticks = 0
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        assert self._task is not None
        self._task.cancel()
        # A cancelled task raises CancelledError when awaited. Swallow it here -- we asked for
        # the cancellation, so it is not an error. Note we still await: dropping a cancelled
        # task without awaiting it is how "Task exception was never retrieved" warnings appear.
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    def expected(self, elapsed: float) -> int:
        return int(elapsed / self.interval)


# ==========================================================================================
# The three ways to spend 0.3 seconds
# ==========================================================================================

WORK_SECONDS = 0.3


def blocking_io() -> str:
    """Stands in for `requests.get(...)`, `psycopg2.execute(...)`, `open(...).read()` --
    any synchronous library call that waits on the network or disk."""
    time.sleep(WORK_SECONDS)
    return "io done"


def cpu_bound() -> int:
    """Stands in for image resizing, PDF parsing, JSON of a 100 MB payload, crypto."""
    deadline = time.perf_counter() + WORK_SECONDS
    total = 0
    while time.perf_counter() < deadline:
        total += sum(i * i for i in range(1000))
    return total


async def measure(label: str, body: object) -> None:
    """Run `body` (an awaitable factory) with a heartbeat alongside and report the damage."""
    async with Heartbeat() as hb:
        started = time.perf_counter()
        await body()  # type: ignore[operator]
        elapsed = time.perf_counter() - started

    expected = hb.expected(elapsed)
    health = "OK" if hb.ticks >= expected * 0.7 else "LOOP BLOCKED"
    print(
        f"{label:<46} {elapsed:5.2f}s  ticks {hb.ticks:>3}/{expected:<3} {health}"
    )


async def main() -> None:
    print(f"\nHeartbeat ticks every 10ms. Each experiment does {WORK_SECONDS}s of work.\n")

    # --- 1. THE BUG ---------------------------------------------------------------------
    # `time.sleep` inside a coroutine. The coroutine never hits an `await`, so it never yields
    # control. The event loop is a single thread running one callback at a time: while this
    # function is on the stack, NOTHING else in the process makes progress. Not the heartbeat,
    # not other requests, not the health endpoint.
    async def bug_blocking_io() -> None:
        blocking_io()

    await measure("async def + time.sleep()   <- THE BUG", bug_blocking_io)

    # --- 2. Also the bug, and harder to spot -------------------------------------------
    # CPU work has no `await` to forget. It is simply not interruptible. Async cannot help
    # here at all -- there is no I/O wait to overlap with.
    async def bug_cpu() -> None:
        cpu_bound()

    await measure("async def + CPU loop      <- ALSO THE BUG", bug_cpu)

    # --- 3. The fix for blocking I/O ----------------------------------------------------
    # `asyncio.to_thread` (3.9+) runs the callable in the default ThreadPoolExecutor and
    # awaits the result. The loop is free the whole time. This works because blocking I/O
    # releases the GIL while it waits, so the thread genuinely parks.
    async def fixed_io_to_thread() -> None:
        await asyncio.to_thread(blocking_io)

    await measure("asyncio.to_thread(blocking_io)", fixed_io_to_thread)

    # --- 4. The fix when the work is genuinely async ------------------------------------
    # If a real async library exists (httpx, asyncpg, pymongo's AsyncMongoClient), use it.
    # `asyncio.sleep` is the stand-in: it yields to the loop instead of holding the thread.
    async def fixed_io_native() -> None:
        await asyncio.sleep(WORK_SECONDS)

    await measure("await asyncio.sleep()  (native async lib)", fixed_io_native)

    # --- 5. The fix for CPU work --------------------------------------------------------
    # A thread does NOT fix CPU work: the GIL means only one thread executes Python bytecode
    # at a time, so the loop thread still gets starved of time slices. A separate *process*
    # does fix it, at the cost of pickling arguments and results.
    async def fixed_cpu_process() -> None:
        loop = asyncio.get_running_loop()
        import concurrent.futures

        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
            await loop.run_in_executor(pool, cpu_bound)

    await measure("run_in_executor(ProcessPool, cpu_bound)", fixed_cpu_process)

    print(
        "\nRead the tick column. Anything far below the expected count means every other\n"
        "request in the process was frozen for that long.\n"
    )

    # --- 6. How you FIND this in production ---------------------------------------------
    # asyncio's debug mode logs any callback that occupies the loop longer than
    # `loop.slow_callback_duration` (default 0.1s). Turning it on in staging is the cheapest
    # way to find accidental blocking calls.
    print("With debug mode on, the loop reports slow callbacks itself:")
    await _demo_debug_mode()


async def _demo_debug_mode() -> None:
    loop = asyncio.get_running_loop()
    loop.set_debug(True)
    loop.slow_callback_duration = 0.05

    import logging

    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = Capture()
    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.addHandler(handler)
    try:
        await asyncio.sleep(0)  # let the loop settle
        time.sleep(0.2)  # the offence
        await asyncio.sleep(0)  # give the loop a chance to notice and log it
    finally:
        asyncio_logger.removeHandler(handler)
        loop.set_debug(False)

    for record in records:
        print("   asyncio WARNING:", record.getMessage().split("\n")[0][:110])
    if not records:
        print("   (no warning captured on this run -- see the README for what it looks like)")


if __name__ == "__main__":
    asyncio.run(main())
