"""Behaviour specification for the retry decorator, shared by the solution and practice suites.

Each `case_*` function takes the `retry` decorator under test, so the identical assertions run
against `retry_backoff.retry` and against whatever you write in `practice_retry_backoff.py`.

Keeping the cases here instead of duplicating them is what makes practice mode honest: you
cannot pass by writing tests that match your implementation.
"""

from __future__ import annotations

import random
import time
from typing import Any

import pytest

# ---------------------------------------------------------------------------------------
# Synchronous behaviour
# ---------------------------------------------------------------------------------------


def case_returns_immediately_when_no_error(retry: Any) -> None:
    calls = []

    @retry(max_attempts=3, base_delay=0.001)
    def works() -> str:
        calls.append(1)
        return "fine"

    assert works() == "fine"
    assert len(calls) == 1, "a succeeding function must be called exactly once"


def case_retries_until_success(retry: Any) -> None:
    calls = []

    @retry(max_attempts=5, base_delay=0.001, jitter=False)
    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("nope")
        return "recovered"

    assert flaky() == "recovered"
    assert len(calls) == 3


def case_reraises_the_last_error(retry: Any) -> None:
    """The most important case: exhausting the retries must NOT return None."""
    calls = []

    @retry(max_attempts=3, base_delay=0.001, jitter=False)
    def always_fails() -> None:
        calls.append(1)
        raise ConnectionError("still down")

    with pytest.raises(ConnectionError, match="still down"):
        always_fails()
    assert len(calls) == 3, "max_attempts counts the first call, not just the retries"


def case_does_not_retry_unlisted_exceptions(retry: Any) -> None:
    calls = []

    @retry(max_attempts=5, base_delay=0.001, exceptions=(ConnectionError,))
    def bad_input() -> None:
        calls.append(1)
        raise ValueError("caller's fault")

    with pytest.raises(ValueError):
        bad_input()
    assert len(calls) == 1, "a non-retryable error must propagate on the first attempt"


def case_preserves_function_metadata(retry: Any) -> None:
    @retry(max_attempts=2, base_delay=0.001)
    def documented(a: int, b: str = "x") -> str:
        """Original docstring."""
        return f"{a}{b}"

    assert documented.__name__ == "documented", "use functools.wraps"
    assert documented.__doc__ == "Original docstring."


def case_passes_through_args_and_kwargs(retry: Any) -> None:
    @retry(max_attempts=2, base_delay=0.001)
    def add(a: int, b: int = 0, *rest: int, **kw: int) -> int:
        return a + b + sum(rest) + sum(kw.values())

    assert add(1, 2, 3, 4, extra=5) == 15


def case_delays_grow_exponentially(retry: Any) -> None:
    """Without jitter the delays must be base, base*factor, base*factor**2, ..."""
    seen: list[float] = []

    @retry(
        max_attempts=4,
        base_delay=0.01,
        factor=2.0,
        jitter=False,
        on_retry=lambda attempt, exc, delay: seen.append(delay),
    )
    def always_fails() -> None:
        raise ConnectionError

    with pytest.raises(ConnectionError):
        always_fails()

    assert seen == pytest.approx([0.01, 0.02, 0.04])


def case_delay_is_capped_by_max_delay(retry: Any) -> None:
    """`max_delay` clamps the exponential growth -- applied BEFORE the sleep happens.

    The numbers are deliberately tiny so the suite stays fast, but the arithmetic is the same
    one that stops attempt 20 from sleeping for six days in production.
    """
    seen: list[float] = []

    @retry(
        max_attempts=5,
        base_delay=0.001,
        factor=10.0,
        max_delay=0.005,
        jitter=False,
        on_retry=lambda attempt, exc, delay: seen.append(delay),
    )
    def fails_fast() -> None:
        raise ConnectionError

    with pytest.raises(ConnectionError):
        fails_fast()

    assert seen == pytest.approx([0.001, 0.005, 0.005, 0.005])
    assert max(seen) <= 0.005


def case_jitter_randomises_within_the_bound(retry: Any) -> None:
    """Full jitter picks uniformly from [0, delay] -- never above it."""
    seen: list[float] = []

    @retry(
        max_attempts=8,
        base_delay=0.001,
        factor=1.0,  # flat, so every uncapped delay is exactly base_delay
        jitter=True,
        rng=random.Random(1234),
        on_retry=lambda attempt, exc, delay: seen.append(delay),
    )
    def always_fails() -> None:
        raise ConnectionError

    with pytest.raises(ConnectionError):
        always_fails()

    assert len(seen) == 7
    assert all(0.0 <= d <= 0.001 for d in seen), "jitter must stay within [0, delay]"
    assert len(set(seen)) > 1, "jittered delays must not all be identical"


def case_rejects_zero_attempts(retry: Any) -> None:
    with pytest.raises(ValueError):
        retry(max_attempts=0)


def case_single_attempt_means_no_retry(retry: Any) -> None:
    calls = []

    @retry(max_attempts=1, base_delay=10.0)
    def always_fails() -> None:
        calls.append(1)
        raise ConnectionError

    started = time.perf_counter()
    with pytest.raises(ConnectionError):
        always_fails()
    assert len(calls) == 1
    assert time.perf_counter() - started < 1.0, "must not sleep when there is no retry left"


# ---------------------------------------------------------------------------------------
# Asynchronous behaviour
# ---------------------------------------------------------------------------------------


async def case_async_retries_until_success(retry: Any) -> None:
    calls = []

    @retry(max_attempts=4, base_delay=0.001, jitter=False)
    async def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError("upstream slow")
        return "recovered"

    assert await flaky() == "recovered"
    assert len(calls) == 3


async def case_async_reraises_the_last_error(retry: Any) -> None:
    @retry(max_attempts=2, base_delay=0.001, jitter=False)
    async def always_fails() -> None:
        raise TimeoutError("still down")

    with pytest.raises(TimeoutError, match="still down"):
        await always_fails()


async def case_async_wrapper_is_awaitable_not_a_coroutine_factory(retry: Any) -> None:
    """Guards against the classic bug: wrapping `async def` in a *sync* wrapper.

    If the decorator does not branch on `iscoroutinefunction`, calling the wrapped function
    returns an un-awaited coroutine object. It never raises, so retries never trigger and the
    body never runs -- a silent no-op in production.
    """
    ran = []

    @retry(max_attempts=3, base_delay=0.001)
    async def records() -> str:
        ran.append(1)
        return "done"

    result = await records()
    assert result == "done", "the wrapper must await the coroutine, not return it"
    assert ran == [1], "the coroutine body must actually have executed"


async def case_async_does_not_block_the_event_loop(retry: Any) -> None:
    """While the retry is backing off, other coroutines must keep running.

    A wrapper that used `time.sleep` instead of `asyncio.sleep` would freeze the whole loop,
    and the ticker below would record far fewer ticks.
    """
    import asyncio

    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.005)
            ticks += 1

    @retry(max_attempts=3, base_delay=0.05, jitter=False)
    async def slow_failure() -> str:
        raise ConnectionError("down")

    tick_task = asyncio.create_task(ticker())
    try:
        with pytest.raises(ConnectionError):
            await slow_failure()
    finally:
        tick_task.cancel()
        # Awaiting a cancelled task raises CancelledError; suppress it so the assertion below
        # is what fails if the behaviour is wrong.
        with pytest.raises(asyncio.CancelledError):
            await tick_task

    # Backoff totals 0.05 + 0.10 = 0.15s. A free event loop fits ~30 ticks in that window;
    # require a conservative floor so the test is not flaky on a loaded machine.
    assert ticks >= 8, f"event loop appears blocked during backoff (only {ticks} ticks)"


SYNC_CASES = [
    case_returns_immediately_when_no_error,
    case_retries_until_success,
    case_reraises_the_last_error,
    case_does_not_retry_unlisted_exceptions,
    case_preserves_function_metadata,
    case_passes_through_args_and_kwargs,
    case_delays_grow_exponentially,
    case_delay_is_capped_by_max_delay,
    case_jitter_randomises_within_the_bound,
    case_rejects_zero_attempts,
    case_single_attempt_means_no_retry,
]

ASYNC_CASES = [
    case_async_retries_until_success,
    case_async_reraises_the_last_error,
    case_async_wrapper_is_awaitable_not_a_coroutine_factory,
    case_async_does_not_block_the_event_loop,
]
