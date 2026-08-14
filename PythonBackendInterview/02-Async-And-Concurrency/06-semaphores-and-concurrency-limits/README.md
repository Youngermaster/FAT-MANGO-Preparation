# Bounded Fan-Out: Semaphores, Worker Pools, Backpressure

> **Prompt as you will hear it:** *"Fetch 1000 URLs, but never more than 10 at a time."*

This is **the** modern async live-coding task for a senior backend role. It is short enough for 20
minutes and deep enough to keep asking questions about: ordering, error handling, cancellation,
memory, backpressure.

---

## Run it

```bash
uv run python 02-Async-And-Concurrency/06-semaphores-and-concurrency-limits/concurrency_limits.py
uv run pytest 02-Async-And-Concurrency/06-semaphores-and-concurrency-limits
```

```
40 jobs, limit=5. 'peak' must never exceed the limit.
  semaphore + gather       peak=5  0.103s  order preserved: True
  worker pool + queue      peak=5  0.103s  order preserved: True
  TaskGroup + semaphore    peak=5  0.104s  order preserved: True

Unbounded vs bounded, 200 jobs:
  unbounded gather  -> peak concurrency 200 (all 200 at once)
  semaphore(limit=5)  -> peak concurrency 5
```

---

## Why bound it at all

Say this before writing any code — it is the part that shows operational experience:

Unbounded `gather` over 1000 URLs opens 1000 sockets at once. That **exhausts your connection
pool**, **hits the file-descriptor limit**, and **DDoSes the dependency you are calling** — quite
possibly your own downstream service. Over a million items it also builds a million Task objects
and runs out of memory before it runs out of sockets. The limit is not a nicety; it is the
difference between a client and a load generator.

---

## 1. Semaphore + gather — the answer to give first

```python
async def map_with_semaphore(func, items, *, limit=10):
    semaphore = asyncio.Semaphore(limit)

    async def bounded(item):
        async with semaphore:  # <-- INSIDE the worker
            return await func(item)

    return await asyncio.gather(*(bounded(i) for i in items))
```

**The one thing to get right:** the semaphore is acquired *inside* the worker, not around the
`gather`. All N tasks are created immediately; each blocks on `acquire()` until a slot frees. Put
the semaphore around the gather instead and you have written something that looks concurrent and
runs strictly serially.

That bug passes a naive "never exceeded the limit" test, which is why the suite here also asserts
the limit is **reached** (`test_actually_reaches_the_limit`). Writing the assertion in both
directions is a nice thing to mention.

`async with` also guarantees release on the exception path. A leaked permit means `limit` failures
exhaust the semaphore and everything after it hangs forever —
`test_semaphore_is_released_when_the_job_raises` guards it.

**Ordering:** `gather` preserves input order regardless of completion order. Free, and worth
saying out loud.

**The caveat to volunteer:** this still creates N Tasks up front. Fine for a thousand items, wrong
for ten million.

---

## 2. Worker pool over a queue — for streams and huge inputs

```python
queue = asyncio.Queue(maxsize=limit * 2)


async def worker():
    while True:
        index, item = await queue.get()
        try:
            results[index] = await func(item)
        finally:
            queue.task_done()  # <-- MUST be in finally


workers = [asyncio.create_task(worker()) for _ in range(limit)]
for pair in enumerate(items):
    await queue.put(pair)  # blocks when full -> backpressure
await queue.join()
for w in workers:
    w.cancel()
```

Only `limit` tasks exist at any moment, no matter how large the input. This is the version for a
paginated API, a Kafka topic, or a ten-million-line file.

Three details interviewers probe:

- **`maxsize` is the backpressure.** Without it the producer races ahead and the queue becomes an
  unbounded in-memory buffer — you have moved the memory problem, not solved it.
- **`task_done()` in a `finally`.** `queue.join()` waits for exactly one `task_done()` per item.
  An exception that skips it hangs the function forever. `test_worker_pool_records_failures_...`
  wraps the call in `wait_for` so that bug shows up as a failure rather than a hung suite.
- **Cancel the workers.** They loop forever by design, so returning without cancelling leaks
  `limit` tasks and the process never exits cleanly.

---

## 3. Streaming results — `imap_unordered`

An async generator that yields each result as it lands, still bounded. Use it when you can act on
each result immediately — stream to the client, write to the DB — so you never hold all N results
in memory.

The subtlety: if the consumer stops early (a `break`, or the HTTP client disconnects), the
generator's `finally` must cancel the outstanding tasks. Otherwise abandoning the loop leaves the
work running.

---

## 4. TaskGroup + semaphore — structured, preferred on 3.11+

Same shape, different failure semantics: one item failing **cancels all in-flight siblings** and
raises an `ExceptionGroup`. Right for all-or-nothing operations, wrong for best-effort fan-out
where you want the other 999 to finish. Choosing between them *is* the interesting question — say
which you'd pick and why.

---

## Follow-ups they will ask next

**"What if one URL fails?"** Three defensible answers, and the point is to name the trade-off:
`return_exceptions=True` to collect failures per item (best-effort); `TaskGroup` to abort
everything (all-or-nothing); or retry inside the worker with backoff and jitter — which composes
with drill `04-Live-Coding-Drills/01-retry-decorator-with-backoff`.

**"Add a timeout per item."** `async with asyncio.timeout(n)` *inside* the worker, so a slow item
does not hold its permit forever. A global timeout around the whole fan-out is a different
requirement — be explicit about which they want.

**"Why not `ThreadPoolExecutor`?"** For network I/O, one coroutine costs a few KB while one thread
costs ~8 MB of stack plus a context switch. Ten thousand coroutines is routine; ten thousand
threads is not. Threads are for blocking libraries you cannot replace.

**"Is `asyncio.Semaphore` thread-safe?"** No. asyncio primitives assume a single loop on a single
thread and are **not** thread-safe — use `threading.Semaphore` across threads, and never `await` a
threading primitive. Confusing the two is a classic error.

**"How does this relate to rate limiting?"** A semaphore bounds *concurrency* (how many at once); a
rate limiter bounds *throughput* (how many per second). Ten concurrent requests each taking 10 ms
is 1000 req/s — well inside a concurrency limit of 10 and well outside a rate limit of 100/s. You
often need both.

**"What if the API returns 429?"** Respect `Retry-After`, back off, and lower the concurrency —
adaptive concurrency (AIMD: additive increase, multiplicative decrease) is the grown-up answer.

---

## Say it out loud

> I create a semaphore with the limit and acquire it *inside* each worker, then gather them all.
> Every task gets created immediately but blocks on acquire until a slot frees, so at most K run
> at once and results still come back in input order. Acquiring around the gather instead is the
> classic bug — it looks concurrent and runs serially. I use `async with` so the permit is
> released even when the call raises, otherwise a few failures exhaust the semaphore and
> everything after it deadlocks. That version creates N tasks up front, which is fine for
> thousands but not for millions — for a stream or a very large input I switch to a worker pool
> reading from an `asyncio.Queue` with a `maxsize`, so only K tasks ever exist and the queue gives
> me backpressure. There, `task_done` has to be in a `finally` or `join` hangs, and the workers
> have to be cancelled at the end because they loop forever. On 3.11+ I'd use a TaskGroup if a
> single failure should abort everything, or `gather(return_exceptions=True)` if it's best-effort.
> And a semaphore limits concurrency, not rate — if the API has a requests-per-second quota I need
> a rate limiter as well.
