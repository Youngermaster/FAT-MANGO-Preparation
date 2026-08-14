"""The version most candidates write first.

It "works" for the happy path, which is exactly why it is dangerous: it passes a quick demo and
then the interviewer starts asking questions. Every numbered comment below is an objection you
should be able to raise *yourself*, before they do. Volunteering these is the difference between
"can write a decorator" and "has run retries in production".

Do not import this module for anything real. It exists to be criticised.
"""

import time


def retry(max_attempts=3, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # noqa: F841
                    print(f"attempt {attempt} failed: {e}")
                    time.sleep(delay)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------------------
# WHAT IS WRONG WITH IT
# ---------------------------------------------------------------------------------------
#
# 1. IT SWALLOWS THE FINAL FAILURE.
#    When every attempt fails, the loop ends and the function falls off the bottom, returning
#    `None`. The caller cannot distinguish "the API returned null" from "we gave up after 3
#    failures". This is the single worst bug here -- it converts a loud error into silent data
#    corruption. Fix: re-`raise` on the last attempt.
#
# 2. IT SLEEPS AFTER THE LAST ATTEMPT.
#    Even the final failing attempt sleeps before giving up, so the caller waits `delay`
#    seconds for nothing. Fix: check `attempt == max_attempts - 1` before sleeping.
#
# 3. NO BACKOFF.
#    A constant delay hammers a struggling service at a fixed rate. Exponential backoff gives
#    it room to recover.
#
# 4. NO JITTER.
#    With deterministic delays, N concurrent workers that failed together retry together --
#    a thundering herd that can keep an already-degraded dependency down.
#
# 5. `except Exception` RETRIES EVERYTHING.
#    A `ValueError` from malformed input will never succeed on retry. You have turned a fast
#    failure into a slow one, and hidden a real bug behind three seconds of sleeping.
#    Worse, catching broad `Exception` in async code is how people accidentally swallow
#    `asyncio.CancelledError` -- although since Python 3.8 that inherits from `BaseException`,
#    so this specific line is safe. Know the distinction; it is a classic follow-up.
#
# 6. NO `functools.wraps`.
#    `flaky.__name__` is now `"wrapper"`, the docstring is gone, and the signature is
#    `(*args, **kwargs)`. That breaks introspection, API docs, and any framework that reads
#    type hints off the function -- FastAPI would fail to build a route from this.
#
# 7. `print` INSTEAD OF `logging`.
#    Unfilterable, unroutable, no levels, no structured fields, writes to stdout in a service
#    whose stdout is a log pipeline.
#
# 8. NO UPPER BOUND ON THE DELAY.
#    Add backoff to this without a `max_delay` and attempt 20 sleeps for six days.
#
# 9. IT SILENTLY BREAKS ON `async def`.
#    Wrapping a coroutine function in a sync wrapper means `func(*args)` returns a coroutine
#    object *without running it*. Creating a coroutine cannot raise, so the "call" always
#    succeeds, the retry logic never triggers, and the caller gets back an un-awaited
#    coroutine. Python emits a RuntimeWarning at garbage-collection time and the actual work
#    never happens. This is the follow-up question you should expect.
#
# 10. UNTESTABLE TIMING.
#    `delay=1` with real `time.sleep` means the test suite takes seconds. Inject the clock, or
#    at minimum let the caller configure a tiny base delay (and a seeded RNG for the jitter).
