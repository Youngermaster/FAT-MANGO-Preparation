"""Retry decorator with exponential backoff and jitter -- sync and async.

This is the single most frequently reported live-coding task for senior Python backend roles.
It is popular because it exercises four things at once: closures, `functools.wraps`, exception
handling, and -- in the follow-up -- your understanding of the difference between blocking and
cooperative sleeping.

Read `README.md` for the interview framing. Read `retry_backoff_naive.py` for the version that
gets you a "looks fine, but..." and then a list of objections.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _compute_delay(
    attempt: int,
    base_delay: float,
    factor: float,
    max_delay: float,
    jitter: bool,
    rng: random.Random,
) -> float:
    """Delay before retry number `attempt` (1-based: attempt 1 is the first *retry*).

    The exponential part is `base_delay * factor ** (attempt - 1)`, clamped at `max_delay` so a
    long-lived worker cannot drift into hour-long sleeps.

    Jitter is "full jitter" from the AWS architecture blog: pick uniformly from `[0, delay]`
    rather than adding a small wobble to a fixed value. This is the part candidates most often
    miss, and interviewers most often ask about.

    Why it matters: if 500 workers all fail against the same downed dependency at the same
    instant, deterministic backoff makes all 500 retry at the same instant too -- you have
    rebuilt the outage as a self-inflicted thundering herd. Randomising the delay spreads the
    retries out and lets the dependency recover.
    """
    delay = min(base_delay * (factor ** (attempt - 1)), max_delay)
    if jitter:
        delay = rng.uniform(0, delay)
    return delay


def retry(
    max_attempts: int = 3,
    *,
    base_delay: float = 0.1,
    factor: float = 2.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, BaseException, float], None] | None = None,
    rng: random.Random | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a callable on failure, with exponential backoff and full jitter.

    Works on both sync and async functions: the returned decorator inspects the target and
    builds the matching wrapper. That matters because an `async def` wrapped in a sync wrapper
    would return a coroutine object that nobody awaits -- the retry would "succeed" instantly
    and silently, because creating a coroutine never raises.

    Args:
        max_attempts: Total attempts including the first one. `max_attempts=3` means one
            initial call plus at most two retries.
        base_delay: Delay before the first retry, in seconds.
        factor: Multiplier applied per subsequent retry.
        max_delay: Upper bound on any single delay, applied before jitter.
        jitter: Randomise each delay over `[0, delay]` to avoid synchronised retry storms.
        exceptions: Only these exception types are retried. Everything else propagates
            immediately -- retrying a `ValueError` from bad input just wastes time and delays
            the error the caller needs to see.
        on_retry: Optional hook `(attempt, exception, delay)` for logging or metrics.
        rng: Inject a seeded `random.Random` to make tests deterministic.

    Returns:
        A decorator preserving the wrapped function's identity via `functools.wraps`.

    Raises:
        ValueError: If `max_attempts` is less than 1.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    _rng = rng if rng is not None else random.Random()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # `iscoroutinefunction` is the branch point. Note it is evaluated once at decoration
        # time, not once per call -- there is no reason to pay for the check on every invocation.
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                for attempt in range(1, max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as exc:
                        # Last attempt: stop swallowing and let the caller see the real error,
                        # with its original traceback intact.
                        if attempt == max_attempts:
                            raise
                        delay = _compute_delay(attempt, base_delay, factor, max_delay, jitter, _rng)
                        if on_retry is not None:
                            on_retry(attempt, exc, delay)
                        logger.warning(
                            "%s failed (attempt %d/%d): %r -- retrying in %.3fs",
                            func.__qualname__,
                            attempt,
                            max_attempts,
                            exc,
                            delay,
                        )
                        # `asyncio.sleep` yields to the event loop. `time.sleep` here would
                        # block every other coroutine in the process for the duration -- the
                        # exact bug interviewers probe for.
                        await asyncio.sleep(delay)
                raise AssertionError("unreachable")  # pragma: no cover

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        raise
                    delay = _compute_delay(attempt, base_delay, factor, max_delay, jitter, _rng)
                    if on_retry is not None:
                        on_retry(attempt, exc, delay)
                    logger.warning(
                        "%s failed (attempt %d/%d): %r -- retrying in %.3fs",
                        func.__qualname__,
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
            raise AssertionError("unreachable")  # pragma: no cover

        return sync_wrapper  # type: ignore[return-value]

    return decorator


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    # --- sync demo -------------------------------------------------------------------
    calls = {"n": 0}

    @retry(max_attempts=4, base_delay=0.01, jitter=False)
    def flaky(succeed_on: int) -> str:
        """Fail until the call counter reaches `succeed_on`."""
        calls["n"] += 1
        if calls["n"] < succeed_on:
            raise ConnectionError(f"boom #{calls['n']}")
        return f"ok after {calls['n']} calls"

    print(flaky(3))

    # `functools.wraps` kept the identity of the original function. Without it, this would
    # print "sync_wrapper" and the docstring would be gone -- which breaks Sphinx, breaks
    # FastAPI's OpenAPI generation, and breaks pickling of decorated functions.
    print("name:", flaky.__name__, "| doc:", flaky.__doc__)

    # --- non-retryable exceptions pass straight through -------------------------------
    @retry(max_attempts=5, base_delay=0.01, exceptions=(ConnectionError,))
    def bad_input() -> None:
        raise ValueError("this is a bug, not a blip -- do not retry it")

    try:
        bad_input()
    except ValueError as exc:
        print("propagated immediately, as it should:", exc)

    # --- async demo -------------------------------------------------------------------
    async def main() -> None:
        state = {"n": 0}

        @retry(max_attempts=3, base_delay=0.01, jitter=False)
        async def flaky_async() -> str:
            state["n"] += 1
            if state["n"] < 3:
                raise TimeoutError("upstream slow")
            return "async ok"

        started = time.perf_counter()
        # Two failures sleeping 0.01s then 0.02s, so total elapsed is about 0.03s -- and
        # crucially the event loop stayed free the whole time.
        print(await flaky_async(), f"in {time.perf_counter() - started:.3f}s")

    asyncio.run(main())
