# Retry Decorator with Exponential Backoff

> **Prompt as you will hear it:** *"Write a decorator that retries a function up to N times with
> exponential backoff."*

---

## Why this one comes up so often

It is the perfect 20-minute senior screen. A junior can produce something that runs; only someone
who has operated a service produces something you would deploy. In one small problem the
interviewer gets to check:

- **Closures and decorator mechanics** — three levels of nesting once the decorator takes arguments.
- **`functools.wraps`** — do you know why identity preservation matters, or do you just cargo-cult it?
- **Exception discipline** — do you re-raise, or silently return `None`?
- **Distributed-systems instinct** — jitter, caps, and *which* exceptions deserve a retry.
- **Async awareness** — the follow-up is always *"now make it work for `async def` too."*

The failure mode is quiet: the naive version passes a live demo. The objections only surface when
the interviewer starts asking. Raise them yourself first.

---

## Files

| File | What it is |
|---|---|
| `retry_backoff.py` | The reference solution, commented as if narrating it out loud |
| `retry_backoff_naive.py` | The version most people write first, plus 10 annotated objections |
| `retry_backoff_cases.py` | The behaviour spec — 15 cases, shared by both suites |
| `practice_retry_backoff.py` | Blank stub. **Start here.** |
| `test_retry_backoff.py` | Spec run against the solution |
| `test_practice_retry_backoff.py` | Same spec run against your stub |

```bash
uv run pytest 04-Live-Coding-Drills/01-retry-decorator-with-backoff              # solution: 15 pass
uv run pytest 04-Live-Coding-Drills/01-retry-decorator-with-backoff -m practice  # your attempt
uv run python 04-Live-Coding-Drills/01-retry-decorator-with-backoff/retry_backoff.py
```

---

## Walkthrough

### The three-layer shape

A decorator that takes arguments is a **function returning a decorator returning a wrapper**:

```python
def retry(max_attempts=3, ...):      # 1. configuration
    def decorator(func):             # 2. receives the function
        @functools.wraps(func)
        def wrapper(*args, **kwargs):  # 3. replaces the function
            ...
        return wrapper
    return decorator
```

`@retry(max_attempts=3)` **calls** `retry` first, and the result is what actually decorates. That
is why the parentheses are mandatory here — `@retry` bare would pass the function in as
`max_attempts`. (Supporting both forms is a real follow-up; see below.)

### The loop, and the one line that matters

```python
for attempt in range(1, max_attempts + 1):
    try:
        return func(*args, **kwargs)
    except exceptions as exc:
        if attempt == max_attempts:
            raise  # <-- this line is the whole exercise
        ...
        time.sleep(delay)
```

Without the bare `raise`, a fully-failed call falls off the end of the loop and returns `None`.
The caller then cannot tell "the upstream returned null" from "we gave up after three failures" —
a loud error silently converted into bad data. Bare `raise` (not `raise exc`) also preserves the
original traceback.

Note the loop is 1-based and `max_attempts` counts the **first call**, so `max_attempts=3` means
one call plus two retries. Say which convention you are using; interviewers do not care which you
pick, they care that you noticed there was a choice.

### Backoff, cap, jitter

```python
delay = min(base_delay * factor ** (attempt - 1), max_delay)
if jitter:
    delay = rng.uniform(0, delay)
```

- **Exponential** gives a struggling dependency progressively more room.
- **`max_delay`** stops attempt 20 from sleeping for six days. Always clamp.
- **Full jitter** — uniform over `[0, delay]`, not "delay plus a wobble".

Jitter is the part candidates skip and interviewers ask about. The argument to make out loud:

> If 500 workers fail against the same downed dependency at the same instant, deterministic
> backoff makes all 500 retry at the same instant too. You have rebuilt the outage as a
> self-inflicted thundering herd. Randomising spreads the load so the dependency can recover.

### Which exceptions to retry

Default-retrying every `Exception` is wrong. A `ValueError` from malformed input will never
succeed on a retry — you have turned a fast failure into a slow one and hidden a real bug behind
three seconds of sleeping. Retry **transient** faults: connection errors, timeouts, HTTP 429/502/
503/504. Never retry 400/401/403/404, and never retry a non-idempotent write unless you have an
idempotency key.

### The async branch

```python
if inspect.iscoroutinefunction(func):
    async def async_wrapper(...):
        ...
        await asyncio.sleep(delay)
```

Two distinct bugs hide here:

1. **Wrapping `async def` in a sync wrapper.** `func(*args)` returns a *coroutine object* without
   running it. Creating a coroutine never raises, so the call always "succeeds", the retry logic
   never triggers, and the caller receives an un-awaited coroutine. Python warns at GC time and
   the work simply never happens. `case_async_wrapper_is_awaitable_not_a_coroutine_factory`
   catches exactly this.
2. **`time.sleep` inside the async wrapper.** It blocks the event loop, freezing every other
   coroutine in the process for the duration. `case_async_does_not_block_the_event_loop` runs a
   ticker alongside the backoff and asserts it kept ticking.

The `iscoroutinefunction` check happens once at decoration time, not per call.

### Testability

Two injection points make the tests fast and deterministic: `on_retry` exposes the computed delay
without patching the clock, and `rng` accepts a seeded `random.Random` so jitter is reproducible.
Being asked *"how would you test this?"* is near-certain — "I inject the clock and the RNG" is the
answer.

---

## Complexity

Time is `O(attempts)` calls plus the sum of the delays; with a cap the total wait is bounded by
`max_attempts * max_delay`. Space is `O(1)`.

---

## Follow-ups they will ask next

**"Make it work with and without parentheses."**
Detect a single callable positional argument:
```python
def retry(func=None, /, **kw):
    if func is not None:
        return retry(**kw)(func)  # used bare as @retry

    def decorator(f): ...

    return decorator
```

**"What if the function is a method?"**
It already works — `self` arrives in `*args`. But be aware that state on `self` mutated by a
failed attempt is *not* rolled back; retries must be idempotent.

**"How is this different from a circuit breaker?"**
Retry is per-call and optimistic. A circuit breaker is per-*dependency* and has memory: after N
consecutive failures it **stops calling at all** for a cooldown, failing fast instead of queueing
work against something known to be down. They compose — breaker outside, retry inside — and
without a breaker, retries amplify load exactly when the system can least afford it.

**"Where would you not use this?"**
Non-idempotent operations without an idempotency key (a retried payment is a double charge); and
anywhere the caller has a deadline shorter than the total backoff — retries must respect the
remaining request budget, not blow through it.

**"What would you use in production?"**
`tenacity` (or `backoff`). Say so. Knowing when *not* to hand-roll is a senior signal — but they
still want to see you can write it.

---

## Say it out loud

> A retry decorator is a three-layer closure: the outer call captures the configuration, the
> middle receives the function, the inner replaces it. The important line is re-raising on the
> final attempt — otherwise an exhausted retry returns `None` and the caller cannot distinguish
> that from a real null. I back off exponentially, clamp with a `max_delay`, and apply full
> jitter, uniform over zero to the delay, so that a fleet of workers that failed together does
> not retry together and turn a recovery into a thundering herd. I only retry transient errors —
> connection failures, timeouts, 429s and 5xxs — because retrying a validation error just delays
> a bug report. For `async def` I branch on `iscoroutinefunction` and use `asyncio.sleep`;
> wrapping a coroutine in a sync wrapper would return an un-awaited coroutine that silently never
> runs, and `time.sleep` would block the whole event loop. In production I would reach for
> `tenacity` and put a circuit breaker in front of it.
