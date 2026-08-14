# Blocking the Event Loop

> **Prompt as you will hear it:** *"What happens if you call `time.sleep(5)` inside an `async def`
> endpoint? What if the endpoint were a plain `def` instead?"*

This is the highest-probability async question for a FastAPI role, and the one that most reliably
separates people who have *used* asyncio from people who have *read about* it. It is also the
production bug you are most likely to be handed on day one.

---

## Run it

```bash
uv run python 02-Async-And-Concurrency/05-blocking-the-loop/blocking_the_loop.py
uv run pytest 02-Async-And-Concurrency/05-blocking-the-loop
```

The script runs a heartbeat coroutine ticking every 10 ms alongside 0.3 s of work, five different
ways, and prints how many ticks survived:

```
async def + time.sleep()   <- THE BUG           0.30s  ticks   0/30  LOOP BLOCKED
async def + CPU loop      <- ALSO THE BUG       0.30s  ticks   0/30  LOOP BLOCKED
asyncio.to_thread(blocking_io)                  0.31s  ticks  27/30  OK
await asyncio.sleep()  (native async lib)       0.30s  ticks  27/30  OK
run_in_executor(ProcessPool, cpu_bound)         0.41s  ticks  31/41  OK
```

**Zero ticks.** For 300 ms, nothing else in the process made progress — no other request, no
health check, no background task. Multiply by real workloads and that is a pod failing its
liveness probe and getting restarted while it is technically "working fine".

---

## The mental model

An event loop is **one thread running one callback at a time**. `async` is cooperative
multitasking: a coroutine keeps the thread until it voluntarily gives it up at an `await` that
actually suspends. There is no preemption, no timer that interrupts you, nothing to rescue you.

So the rule is short:

> **Between two `await`s, you own the entire process.**

`time.sleep(5)` contains no `await`. Neither does a CPU loop, a `requests.get`, or a synchronous
database driver. While any of them is on the stack, the loop cannot run anything else.

Your Node.js background transfers exactly here — same single-threaded event loop, same "don't
block it" rule. Say that if it helps you explain, but use Python's vocabulary.

### `asyncio.sleep` vs `time.sleep`

The single most-confused pair in Python.

| | What it does |
|---|---|
| `time.sleep(n)` | Parks **the thread**. The loop is stuck. |
| `await asyncio.sleep(n)` | Schedules a wake-up and **yields to the loop**, which runs everything else meanwhile. |

Same for `requests` vs `httpx.AsyncClient`, `psycopg2` vs `asyncpg`, `pymongo.MongoClient` vs
`pymongo.AsyncMongoClient`.

---

## The FastAPI-specific half of the answer

This is the part interviewers really want, and it is counter-intuitive:

| Endpoint | Where it runs | A blocking call inside it |
|---|---|---|
| `async def` | On the event loop | **Freezes the whole server** |
| `def` (plain) | In Starlette's `anyio` threadpool | Fine — only occupies one worker thread |

So a *sync* endpoint is **safer** for blocking work than an async one. If you are calling a
synchronous library and cannot change it, declaring the endpoint `def` is the correct answer, not a
fallback.

The same rule applies to **dependencies**: a `def` dependency also goes to the threadpool, an
`async def` one does not.

The catch: that threadpool is bounded (40 tokens by default in AnyIO). Enough concurrent `def`
endpoints all blocking, and requests queue waiting for a thread — the symptom is latency climbing
under load with CPU near idle.

**The worst of both worlds** — and the thing to name as the actual bug — is `async def` plus a
synchronous library. You get none of the threadpool's protection and all of the loop's fragility.

---

## The decision table

| Work | Do this | Not this |
|---|---|---|
| I/O with a native async library | `await` it | — |
| Blocking I/O, library can't change | `await asyncio.to_thread(fn)` or a `def` endpoint | calling it in `async def` |
| CPU-bound | `run_in_executor(ProcessPoolExecutor, fn)`, or a real task queue | a thread |
| Fire-and-forget follow-up work | `asyncio.create_task` (keep a reference!) or a job queue | blocking the response |

**Why a thread does not fix CPU work:** the GIL means only one thread executes Python bytecode at a
time, so a CPU-burning thread still starves the loop thread of time slices. A separate *process*
sidesteps the GIL, at the cost of pickling arguments and results. (Python 3.14's free-threaded
build changes this — see `10-free-threaded-python/`.)

**`to_thread` vs `run_in_executor`:** `asyncio.to_thread` (3.9+) is the ergonomic wrapper over the
default thread executor. Use `run_in_executor` when you need a *specific* pool — above all a
`ProcessPoolExecutor`, which `to_thread` cannot give you.

---

## The trap inside the trap

`asyncio.gather` does **not** rescue blocking calls. Concurrency comes from coroutines yielding; if
they never yield, `gather` runs them strictly one after another and the total is the **sum**, not
the max. The test suite proves it: three 0.15 s blocking calls under `gather` take ~0.45 s, while
three `to_thread` calls take ~0.15 s.

This is why "I wrapped it in `gather` and it didn't get faster" is such a common bug report.

---

## How you find it in production

Name at least two of these:

1. **asyncio debug mode.** `PYTHONASYNCIODEBUG=1`, or `asyncio.run(main(), debug=True)`. The loop
   logs any callback exceeding `loop.slow_callback_duration` (default 0.1 s):
   `Executing <Task ...> took 0.201 seconds`. The script demonstrates this live.
2. **`py-spy dump --pid <pid>`.** Attaches to a running process without restarting it and shows
   what every thread is doing right now. If the loop thread is inside `time.sleep` or your JSON
   parser, you have found it.
3. **An event-loop lag metric.** Schedule a callback for 10 ms from now, measure how late it
   actually fires, and export the delta. Rising loop lag is the leading indicator, and it belongs
   on a dashboard next to request latency.
4. `BlockBuster` / `blockbuster` style libraries that monkeypatch known-blocking stdlib calls and
   raise if they are invoked on the loop — useful in tests.

The symptom that should make you suspect this: **p99 latency collapses under load while CPU sits
idle**, and slow requests are slow in a *correlated* way — everything gets slow at once, rather
than one endpoint being slow.

---

## Follow-ups they will ask next

**"How many uvicorn workers should you run?"** Roughly one process per core for CPU-bound work
(`gunicorn -k uvicorn.workers.UvicornWorker -w $(nproc)`); for I/O-bound async services, fewer
processes are fine because a single loop handles thousands of concurrent sockets. Workers are
about using cores and isolating crashes, not about concurrency within a request.

**"Does `async` make my code faster?"** No — it makes it *scale* under I/O concurrency. A single
request is not faster; you just serve far more of them per process while they wait. If the work is
CPU-bound, async makes things marginally *worse* (event-loop overhead with no wait to overlap).

**"What about `asyncio.to_thread` and the GIL?"** It works for I/O because blocking I/O releases
the GIL while it waits. It also works for GIL-releasing C extensions (numpy, zlib, `ssl`,
compression, image codecs). It does nothing for pure-Python CPU work.

---

## Say it out loud

> An event loop is one thread running one callback at a time, and `async` is cooperative — a
> coroutine holds the thread until it hits an `await` that actually suspends. So `time.sleep`
> inside an `async def` freezes the entire process: every other request, every background task,
> the health endpoint, all of it. `asyncio.sleep` is the opposite — it yields to the loop. In
> FastAPI specifically the answer flips depending on how the endpoint is declared: a plain `def`
> endpoint runs in Starlette's threadpool, so a blocking call there only costs one worker thread,
> while an `async def` endpoint runs on the loop and takes the whole server down with it. The
> worst combination is `async def` calling a synchronous library. The fixes are: use a native
> async client if one exists, `asyncio.to_thread` for blocking I/O you cannot change, and a
> process pool or a real task queue for CPU-bound work — a thread will not help there because of
> the GIL. To find it in production I would turn on asyncio debug mode, which logs slow callbacks,
> use `py-spy dump` on the live process, and track event-loop lag as a metric. The giveaway is p99
> latency collapsing under load while CPU is idle.
