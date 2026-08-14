# gather vs TaskGroup vs as_completed vs wait

> **Prompt as you will hear it:** *"You need to call five services concurrently. How do you do it?
> What happens if one of them fails?"*

The first half is easy and everyone answers it. **The second half is the question.** Each
primitive has different failure semantics, and choosing wrong leaks tasks that keep running after
you have already returned an error to the caller.

---

## Run it

```bash
uv run python 02-Async-And-Concurrency/03-gather-taskgroup-as-completed/orchestration.py
uv run pytest 02-Async-And-Concurrency/03-gather-taskgroup-as-completed
```

---

## The table to know cold

| Primitive | On child failure | Returns | Use when |
|---|---|---|---|
| `gather(*aws)` | Raises the **first** exception; **siblings keep running** | ordered list | legacy code, or you genuinely want fail-fast without cleanup |
| `gather(..., return_exceptions=True)` | Nothing raises; failures come back **as values** | ordered list, mixed | best-effort fan-out |
| `TaskGroup()` (3.11+) | **Cancels all siblings**, raises `ExceptionGroup` | nothing — hold task handles | **the default** |
| `as_completed(aws)` | Raises when you `await` that one | iterator, **completion order** | streaming results, early exit |
| `wait(aws, return_when=…)` | **Nothing** — no raise, no cancel | `(done, pending)` sets | you want full manual control |
| `asyncio.timeout(n)` (3.11+) | Cancels the body, raises `TimeoutError` | — | deadlines |

Ordering matters in results too: **`gather` preserves submission order; `as_completed` gives you
completion order.**

---

## `gather`'s sharp edge

```python
try:
    await asyncio.gather(fast(), boom(), slow())
except ValueError:
    return {"error": "upstream failed"}  # ...and slow() is STILL RUNNING
```

`gather` re-raises the first exception immediately but never cancels the others. You return a 500
to the client while `slow()` continues in the background — holding a DB connection, maybe writing
a half-finished record. The demo proves it: after handling the error, waiting 0.25 s shows `slow`
completed anyway.

`test_gather_does_not_cancel_siblings` asserts exactly this, including that
`tasks[1].cancelled()` is `False`.

**`return_exceptions=True` gotcha:** results are not filtered for you. Forget the
`isinstance(r, Exception)` check and you hand an exception object downstream as if it were data —
a `TypeError` five frames away from the real cause.

---

## Why `TaskGroup` is the modern default

**Structured concurrency** means the `async with` block cannot be exited while children are alive.
Normal exit or exception, every task it spawned is finished or cancelled by the time you leave.
Task leaks become impossible *by construction* rather than by discipline.

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(fetch_user(uid))
    tg.create_task(fetch_orders(uid))
    tg.create_task(fetch_prefs(uid))
# past this line: all three are done, or all three were cancelled
```

Two consequences to mention:

**It raises `ExceptionGroup`, not the exception.** Catch it with `except*`:

```python
except* ValueError as eg:
    for exc in eg.exceptions: ...
```

That is not ceremony — several children can fail simultaneously, and `gather` structurally cannot
report more than one. `test_taskgroup_reports_every_simultaneous_failure` shows both surviving.

**It returns nothing.** Keep the `Task` objects and read `.result()` after the block.

---

## `as_completed` and the early exit

Use it to act on each result as it lands — streaming to the client, writing to a queue — or to
take the first good answer and abandon the rest:

```python
for future in asyncio.as_completed(tasks):
    winner = await future
    break
for t in tasks:
    t.cancel()  # <-- as_completed will NOT do this for you
await asyncio.gather(*tasks, return_exceptions=True)
```

Breaking out of the loop without that cleanup leaves the losers running. Also note you lose the
association with the input unless you carry the identity in the result.

---

## `wait` is the footgun

`wait(..., return_when=FIRST_COMPLETED)` does the least of any of them: it does not cancel, and it
does not raise. It hands you `(done, pending)` and walks away. Two bugs follow:

1. Forget to cancel `pending` and those tasks keep running — the classic leaked-connection bug.
2. Forget to inspect `done` and child exceptions vanish silently.

Since 3.12 it also requires **Tasks**, not bare coroutines. Reach for `wait` only when you truly
want manual control; `TaskGroup` or `as_completed` covers almost every real case.

---

## The fire-and-forget hazard

```python
asyncio.create_task(send_email(...))  # BUG
```

The loop keeps only a **weak** reference. If nothing else holds the task it can be
garbage-collected mid-flight and simply stop. And an exception inside an un-awaited task is
swallowed until GC eventually logs *"Task exception was never retrieved"*.

The documented idiom:

```python
background: set[asyncio.Task] = set()

task = asyncio.create_task(send_email(...))
background.add(task)
task.add_done_callback(background.discard)
```

In a web service the better answer is usually *don't* fire-and-forget — use a durable queue, since
an in-process task dies with the pod.

---

## Coroutines vs Tasks vs Futures

Expect this as a direct question:

- A **coroutine** is inert. Calling `foo()` runs no code; it builds an object. Forgetting `await`
  gives you a `RuntimeWarning: coroutine was never awaited` and silently skipped work.
- A **Task** is a `Future` subclass that *drives* a coroutine on the loop. `create_task` is what
  makes something run concurrently. This is why `gather(a(), b())` is concurrent — `gather` wraps
  each coroutine in a Task.
- A **Future** is a low-level placeholder for a result, usually produced when bridging
  callback-style APIs. You rarely create one directly.

---

## Follow-ups they will ask next

**"How do you limit concurrency to 10?"** `asyncio.Semaphore` inside each worker, or a worker-pool
over an `asyncio.Queue`. Unbounded `gather` over a million URLs builds a million Tasks and runs out
of memory before it runs out of sockets. See `06-semaphores-and-concurrency-limits/`.

**"How do you add a timeout?"** `async with asyncio.timeout(n):` (3.11+) over `asyncio.wait_for` —
it composes as a context manager, wraps a whole block, and uses cancel-counting so nested timeouts
attribute correctly. Nesting it around a `TaskGroup` cancels every child; the test proves it.

**"`gather` vs `TaskGroup` — which and why?"** TaskGroup unless you need `return_exceptions=True`
semantics. Say that plainly; hedging reads as not having an opinion.

**"What about `anyio`?"** Same structured-concurrency model (task groups / nurseries, cancel
scopes), borrowed from Trio, and it runs on both asyncio and Trio. Worth naming — Starlette and
FastAPI are built on it, which is why `def` endpoints land in *AnyIO's* threadpool.

---

## Say it out loud

> They differ in what happens to the siblings when one child fails. `gather` raises the first
> exception but does not cancel the others, so you can return an error to the caller while work is
> still running in the background — a real leak. `gather(return_exceptions=True)` collects
> failures as values instead, which is right for best-effort fan-out, as long as you remember to
> filter the results for exception instances. `TaskGroup` is my default: it is structured, so the
> block cannot exit while children are alive, a failure cancels the siblings, and you get an
> `ExceptionGroup` that can carry several simultaneous failures — which `gather` structurally
> cannot. You catch it with `except*` and read results off the task handles. `as_completed` gives
> results in completion order, good for streaming or first-good-answer, but it will not cancel the
> losers for you. And `wait` neither raises nor cancels — it just hands back done and pending, so
> it is the easiest one to leak with. For deadlines I use `async with asyncio.timeout(...)` rather
> than `wait_for`. One more thing: a bare `create_task` needs a strong reference kept somewhere,
> or it can be garbage collected mid-flight.
