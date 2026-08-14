"""gather vs TaskGroup vs as_completed vs wait -- what each one does when a child fails.

Run it:

    uv run python 02-Async-And-Concurrency/03-gather-taskgroup-as-completed/orchestration.py

The interesting question is never "how do I run things concurrently". It is "what happens to the
*other* five when the third one raises". Each primitive answers that differently, and picking the
wrong one leaks tasks that keep running after you have already returned an error to the caller.
"""

from __future__ import annotations

import asyncio
from typing import Any

# Tracks which workers actually ran to completion, so we can see what got cancelled.
completed: list[str] = []


async def work(name: str, delay: float, *, fail: bool = False) -> str:
    """A unit of work that may fail partway through."""
    await asyncio.sleep(delay)
    if fail:
        raise ValueError(f"{name} failed")
    completed.append(name)
    return f"{name} ok"


def reset() -> None:
    completed.clear()


# ==========================================================================================
# 1. gather -- the legacy default
# ==========================================================================================


async def demo_gather_propagates_first_error() -> None:
    """`gather` re-raises the first exception IMMEDIATELY, but does NOT cancel the siblings.

    This is the sharp edge. `gather` returns as soon as one child raises, so your code proceeds
    to handle the error -- while the other coroutines are still running in the background,
    holding connections, writing to the database, and eventually logging warnings nobody reads.
    """
    reset()
    try:
        await asyncio.gather(
            work("fast", 0.01),
            work("boom", 0.02, fail=True),
            work("slow", 0.20),
        )
    except ValueError as exc:
        print(f"  gather raised {exc!r} after ~0.02s; completed so far: {completed}")

    # Prove the survivor kept going after we already handled the error.
    await asyncio.sleep(0.25)
    print(f"  ...0.25s later, 'slow' had still been running: completed={completed}")


async def demo_gather_return_exceptions() -> None:
    """`return_exceptions=True` collects failures as values instead of raising.

    Now every child runs to completion and you get a positional list of results-or-exceptions.
    Right choice for best-effort fan-out (notify 50 subscribers, don't let one bad webhook
    abort the rest). Wrong choice if a failure means the whole operation is meaningless.

    The gotcha: results are NOT filtered for you. Forgetting to check
    `isinstance(r, Exception)` means you hand an exception object downstream as if it were data.
    """
    reset()
    results = await asyncio.gather(
        work("a", 0.01),
        work("b", 0.02, fail=True),
        work("c", 0.03),
        return_exceptions=True,
    )
    ok = [r for r in results if not isinstance(r, BaseException)]
    failed = [r for r in results if isinstance(r, BaseException)]
    print(f"  results are positional: {results}")
    print(f"  -> {len(ok)} succeeded, {len(failed)} failed; all children ran: {completed}")


# ==========================================================================================
# 2. TaskGroup (3.11+) -- structured concurrency, the modern default
# ==========================================================================================


async def demo_taskgroup_cancels_siblings() -> None:
    """A failing child CANCELS its siblings, and the group raises an ExceptionGroup.

    'Structured' means the block cannot be exited while children are still running. When the
    `async with` ends -- normally or by exception -- every task it spawned is finished or
    cancelled. No leaks, by construction.
    """
    reset()
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(work("fast", 0.01))
            tg.create_task(work("boom", 0.02, fail=True))
            tg.create_task(work("slow", 0.20))  # will be cancelled at ~0.02s
    except* ValueError as eg:
        # `except*` unpacks an ExceptionGroup. Multiple children can fail simultaneously, so
        # the group carries ALL of them -- something plain `gather` cannot express.
        print(f"  TaskGroup raised ExceptionGroup with {len(eg.exceptions)} error(s): "
              f"{[str(e) for e in eg.exceptions]}")

    await asyncio.sleep(0.25)
    print(f"  'slow' was cancelled, so it never completed: completed={completed}")


async def demo_taskgroup_collects_multiple_failures() -> None:
    """Two children failing at once produce two exceptions in the group."""
    reset()
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(work("boom1", 0.01, fail=True))
            tg.create_task(work("boom2", 0.01, fail=True))
    except* ValueError as eg:
        print(f"  both failures preserved: {sorted(str(e) for e in eg.exceptions)}")


async def demo_taskgroup_results() -> None:
    """TaskGroup returns nothing -- hold the Task objects and read `.result()` afterwards."""
    reset()
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(work(f"w{i}", 0.01 * i)) for i in range(1, 4)]
    print(f"  results via task handles: {[t.result() for t in tasks]}")


# ==========================================================================================
# 3. as_completed -- results in the order they finish
# ==========================================================================================


async def demo_as_completed() -> None:
    """Stream results as they arrive instead of waiting for the slowest.

    Use it when you can act on each result immediately (write to a queue, stream to the client)
    or want to bail out early once you have enough. Note the yield order is completion order,
    so you lose the association with the input unless you carry it in the result.
    """
    reset()
    coros = [work("slow", 0.05), work("medium", 0.03), work("fast", 0.01)]
    order: list[str] = []
    for future in asyncio.as_completed(coros):
        order.append(await future)
    print(f"  arrival order (not submission order): {order}")


async def demo_as_completed_early_exit() -> None:
    """First-good-answer: take the winner and cancel the rest.

    The manual cancellation is the part people forget -- `as_completed` will not clean up for
    you, so breaking out of the loop leaves the losers running.
    """
    reset()
    tasks = [
        asyncio.create_task(work("replica-a", 0.20)),
        asyncio.create_task(work("replica-b", 0.01)),
        asyncio.create_task(work("replica-c", 0.20)),
    ]
    winner = None
    for future in asyncio.as_completed(tasks):
        winner = await future
        break
    for task in tasks:
        task.cancel()  # <-- without this, the losers keep running
    await asyncio.gather(*tasks, return_exceptions=True)
    print(f"  winner={winner!r}, losers cancelled; completed={completed}")


# ==========================================================================================
# 4. wait -- the low-level one, and its footgun
# ==========================================================================================


async def demo_wait_leaves_pending_tasks_running() -> None:
    """`wait(..., return_when=FIRST_COMPLETED)` hands back (done, pending) and does NOTHING else.

    It does not cancel, it does not raise. If you forget to cancel `pending`, those tasks keep
    running -- the classic "why is this connection still open" leak. Also note `wait` requires
    Tasks, not bare coroutines, since 3.12.
    """
    reset()
    tasks = [
        asyncio.create_task(work("quick", 0.01)),
        asyncio.create_task(work("lingering", 0.20)),
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    print(f"  done={len(done)} pending={len(pending)} -- and pending is still RUNNING")
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    print(f"  after explicit cancellation: completed={completed}")


# ==========================================================================================
# 5. The fire-and-forget hazard
# ==========================================================================================


async def demo_unreferenced_task_can_vanish() -> None:
    """`asyncio.create_task(...)` without keeping a reference is a real bug.

    The loop holds only a WEAK reference to the task. If nothing else references it, it can be
    garbage-collected mid-flight and simply stop. Worse, an exception inside an un-awaited task
    is swallowed until GC logs 'Task exception was never retrieved'.

    The fix is the documented idiom: keep a strong reference in a set and discard on completion.
    """
    background: set[asyncio.Task[Any]] = set()

    async def fire_and_forget() -> None:
        await asyncio.sleep(0.01)
        completed.append("background")

    reset()
    task = asyncio.create_task(fire_and_forget())
    background.add(task)                       # strong reference
    task.add_done_callback(background.discard)  # and release it when finished
    await asyncio.sleep(0.05)
    print(f"  background task survived: completed={completed}, set drained: {not background}")


async def main() -> None:
    sections = [
        ("gather: first error propagates, siblings keep running", demo_gather_propagates_first_error),
        ("gather(return_exceptions=True): collect everything", demo_gather_return_exceptions),
        ("TaskGroup: sibling cancellation + ExceptionGroup", demo_taskgroup_cancels_siblings),
        ("TaskGroup: multiple simultaneous failures", demo_taskgroup_collects_multiple_failures),
        ("TaskGroup: getting results out", demo_taskgroup_results),
        ("as_completed: arrival order", demo_as_completed),
        ("as_completed: first good answer wins", demo_as_completed_early_exit),
        ("wait(FIRST_COMPLETED): you must cancel pending yourself", demo_wait_leaves_pending_tasks_running),
        ("create_task: keep a reference or it may vanish", demo_unreferenced_task_can_vanish),
    ]
    for title, demo in sections:
        print(f"\n{title}")
        print("-" * len(title))
        await demo()


if __name__ == "__main__":
    asyncio.run(main())
