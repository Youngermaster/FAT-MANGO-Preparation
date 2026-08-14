"""PRACTICE STUB -- write this from scratch, then run:

    uv run pytest 04-Live-Coding-Drills/01-retry-decorator-with-backoff -m practice

Do not open `retry_backoff.py` until you have either passed or genuinely stalled for 10 minutes.
The interview forbids AI assistance and reportedly happens in a plain editor, so the only useful
practice is the kind where nothing helps you.

Target: all 15 cases green. Budget: 20 minutes for the sync version, 5 more for async.

Checklist to satisfy (each maps to a test):
  - returns the value on first success, calling the function exactly once
  - retries on failure and returns once it succeeds
  - RE-RAISES the final exception instead of returning None
  - only retries the exception types in `exceptions`
  - preserves __name__ / __doc__ (functools.wraps)
  - forwards *args and **kwargs untouched
  - delays grow base, base*factor, base*factor**2 ...
  - each delay is clamped to max_delay
  - jitter picks uniformly from [0, delay]
  - raises ValueError for max_attempts < 1
  - max_attempts=1 means one call and no sleep
  - works on `async def` too, awaiting with asyncio.sleep (not time.sleep)
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


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
    """Retry a sync or async callable with exponential backoff and full jitter."""
    raise NotImplementedError("Write me from scratch. No peeking, no autocomplete.")


if __name__ == "__main__":
    calls = {"n": 0}

    @retry(max_attempts=4, base_delay=0.01, jitter=False)
    def flaky() -> str:
        """Fail twice, then succeed."""
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError(f"boom #{calls['n']}")
        return f"ok after {calls['n']} calls"

    print(flaky())
