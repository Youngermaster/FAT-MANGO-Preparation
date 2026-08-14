"""Locks in the semantic differences between the orchestration primitives."""

from __future__ import annotations

import asyncio

import pytest


async def _work(log: list[str], name: str, delay: float, *, fail: bool = False) -> str:
    await asyncio.sleep(delay)
    if fail:
        raise ValueError(f"{name} failed")
    log.append(name)
    return name


# ------------------------------------------------------------------------------------------
# gather
# ------------------------------------------------------------------------------------------


async def test_gather_raises_the_first_exception() -> None:
    log: list[str] = []
    with pytest.raises(ValueError, match="boom failed"):
        await asyncio.gather(
            _work(log, "a", 0.01),
            _work(log, "boom", 0.02, fail=True),
        )


async def test_gather_does_not_cancel_siblings() -> None:
    """The sharp edge: `gather` returns on first error while the others keep running."""
    log: list[str] = []
    tasks = [
        asyncio.create_task(_work(log, "boom", 0.01, fail=True)),
        asyncio.create_task(_work(log, "survivor", 0.10)),
    ]
    with pytest.raises(ValueError):
        await asyncio.gather(*tasks)

    assert "survivor" not in log, "sanity: it should not have finished yet"
    assert not tasks[1].cancelled(), "gather must NOT have cancelled the sibling"

    await asyncio.sleep(0.15)
    assert "survivor" in log, "the sibling kept running after the error was handled"


async def test_gather_return_exceptions_collects_everything_positionally() -> None:
    log: list[str] = []
    results = await asyncio.gather(
        _work(log, "a", 0.01),
        _work(log, "b", 0.01, fail=True),
        _work(log, "c", 0.01),
        return_exceptions=True,
    )
    assert results[0] == "a"
    assert isinstance(results[1], ValueError)
    assert results[2] == "c"
    assert sorted(log) == ["a", "c"], "every non-failing child ran to completion"


# ------------------------------------------------------------------------------------------
# TaskGroup
# ------------------------------------------------------------------------------------------


async def test_taskgroup_cancels_siblings_on_failure() -> None:
    log: list[str] = []
    slow: asyncio.Task[str] | None = None

    with pytest.raises(BaseExceptionGroup) as caught:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(_work(log, "boom", 0.01, fail=True))
            slow = tg.create_task(_work(log, "slow", 0.50))

    assert slow is not None
    assert slow.cancelled(), "TaskGroup must cancel siblings when a child fails"
    assert "slow" not in log
    assert len(caught.value.exceptions) == 1


async def test_taskgroup_reports_every_simultaneous_failure() -> None:
    """`gather` can only surface one exception. An ExceptionGroup carries them all."""
    log: list[str] = []
    with pytest.raises(BaseExceptionGroup) as caught:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(_work(log, "boom1", 0.01, fail=True))
            tg.create_task(_work(log, "boom2", 0.01, fail=True))

    messages = sorted(str(e) for e in caught.value.exceptions)
    assert messages == ["boom1 failed", "boom2 failed"]


async def test_taskgroup_waits_for_all_children_before_exiting() -> None:
    """Structured concurrency: the block cannot be left while children are alive."""
    log: list[str] = []
    async with asyncio.TaskGroup() as tg:
        for i in range(5):
            tg.create_task(_work(log, f"w{i}", 0.01 * (i + 1)))
    assert len(log) == 5, "every child must be finished by the time the block exits"


async def test_taskgroup_results_come_from_task_handles() -> None:
    log: list[str] = []
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_work(log, f"w{i}", 0.001)) for i in range(3)]
    assert [t.result() for t in tasks] == ["w0", "w1", "w2"]


# ------------------------------------------------------------------------------------------
# as_completed
# ------------------------------------------------------------------------------------------


async def test_as_completed_yields_in_completion_order() -> None:
    log: list[str] = []
    coros = [
        _work(log, "slow", 0.05),
        _work(log, "medium", 0.03),
        _work(log, "fast", 0.01),
    ]
    arrival = [await fut for fut in asyncio.as_completed(coros)]
    assert arrival == ["fast", "medium", "slow"]


async def test_as_completed_does_not_cancel_the_losers_for_you() -> None:
    log: list[str] = []
    tasks = [
        asyncio.create_task(_work(log, "winner", 0.01)),
        asyncio.create_task(_work(log, "loser", 0.10)),
    ]
    for fut in asyncio.as_completed(tasks):
        await fut
        break

    assert not tasks[1].done(), "breaking out of the loop leaves the rest running"

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    assert "loser" not in log


# ------------------------------------------------------------------------------------------
# wait
# ------------------------------------------------------------------------------------------


async def test_wait_returns_pending_without_cancelling_them() -> None:
    log: list[str] = []
    tasks = [
        asyncio.create_task(_work(log, "quick", 0.01)),
        asyncio.create_task(_work(log, "lingering", 0.10)),
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    assert len(done) == 1
    assert len(pending) == 1
    assert not next(iter(pending)).cancelled(), "wait never cancels; that is your job"

    for task in pending:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def test_wait_does_not_raise_child_exceptions() -> None:
    """Unlike gather, `wait` returns the failed task rather than re-raising. Silently
    ignoring the done set is how failures disappear."""
    log: list[str] = []
    task = asyncio.create_task(_work(log, "boom", 0.01, fail=True))
    done, _ = await asyncio.wait([task])

    finished = next(iter(done))
    assert isinstance(finished.exception(), ValueError), "you must inspect the result yourself"


# ------------------------------------------------------------------------------------------
# timeouts
# ------------------------------------------------------------------------------------------


async def test_asyncio_timeout_cancels_the_body() -> None:
    log: list[str] = []
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.02):
            await _work(log, "too-slow", 0.50)
    assert "too-slow" not in log


async def test_timeout_inside_taskgroup_cancels_all_children() -> None:
    log: list[str] = []
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.02):
            async with asyncio.TaskGroup() as tg:
                tg.create_task(_work(log, "a", 0.50))
                tg.create_task(_work(log, "b", 0.50))
    assert log == []
