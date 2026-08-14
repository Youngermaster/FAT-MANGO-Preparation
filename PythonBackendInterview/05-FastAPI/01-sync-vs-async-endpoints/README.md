# `def` vs `async def` Endpoints

> **Prompt as you will hear it:** *"What happens if you call a blocking function inside an
> `async def` endpoint? What if the endpoint were a plain `def`?"*

The highest-probability FastAPI question, and the answer surprises people: **the plain `def`
endpoint is the safer one for blocking work.**

---

## Run it

```bash
uv run python 05-FastAPI/01-sync-vs-async-endpoints/sync_vs_async.py
uv run pytest 05-FastAPI/01-sync-vs-async-endpoints
```

Four concurrent requests, each doing 0.25 s of work, with a health-check poller running alongside:

```
  endpoint               total  health hits   verdict
  -------------------- -------  -----------   ------------------------------
  /async-blocking        1.02s            1   serialised AND froze the loop
  /sync-blocking         0.29s           42   threadpool: concurrent, loop free
  /async-proper          0.25s           39   native async: concurrent, loop free
  /async-offloaded       0.26s           41   to_thread: concurrent, loop free
```

`/async-blocking` took **4× longer** *and* served **one** health check instead of forty. That
second number is the real story: the damage was not confined to the slow endpoint, it took down
the whole server.

---

## Why

Starlette inspects your handler:

| You wrote | Starlette does | A blocking call inside costs |
|---|---|---|
| `async def` | awaits it **on the event loop** | **the entire server** |
| `def` | `run_in_threadpool(handler)` via AnyIO | **one worker thread** |

`async` is cooperative. A coroutine holds the loop thread until it hits an `await` that actually
suspends. `time.sleep`, `requests.get`, `psycopg2`, `pymongo.MongoClient` — none of them contain
an `await`, so the loop cannot run anything else while they are on the stack.

A `def` handler never touches the loop. Starlette hands it to a thread and awaits the *thread*, so
the loop stays free.

**So the rule is:** if you are calling a synchronous library and cannot change it, declaring the
endpoint `def` is the **correct** answer, not a workaround.

**Dependencies follow the identical rule.** A `def` dependency goes to the threadpool; an
`async def` one runs on the loop. Same trap, less often noticed.

---

## The catch with the `def` answer

That threadpool is **bounded** — AnyIO's default limiter carries **40 tokens**. Beyond 40
concurrent blocking handlers, requests queue waiting for a thread. The demo shows it: 60
concurrent requests to `/sync-blocking` take 0.53 s instead of 0.25 s because 20 of them waited.

The production symptom is distinctive and worth naming: **latency climbs under load while CPU sits
near idle**, and everything gets slow together rather than one endpoint degrading.

You can raise it (`anyio.to_thread.current_default_thread_limiter().total_tokens = 100`) but that
is a band-aid — each thread costs ~8 MB of stack, and the real fix is a native async client.

---

## The decision table

| Situation | Do this |
|---|---|
| Native async library exists (`httpx`, `asyncpg`, `AsyncMongoClient`) | `async def` + `await` |
| Blocking library, cannot change it | `def` endpoint, **or** `async def` + `await asyncio.to_thread(fn)` |
| CPU-bound (image resize, PDF parse, crypto) | `run_in_executor(ProcessPoolExecutor, …)` or a task queue — **not** a thread |
| Mixed: async I/O plus one blocking call | `async def` + `to_thread` for just that call |

**The worst combination**, and the actual bug you will be handed in production, is `async def`
calling a synchronous library. You get none of the threadpool's protection and all of the loop's
fragility.

**Why a thread does not fix CPU work:** the GIL means one thread executes Python bytecode at a
time, so a CPU-burning thread still starves the loop. A separate *process* sidesteps it, at the
cost of pickling arguments and results.

---

## Testing FastAPI in 2026 — two things every old tutorial gets wrong

The test file is worth reading for these alone:

```python
transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
    ...
```

1. **`httpx.AsyncClient(app=app)` was removed in httpx 0.28.** The explicit `ASGITransport` is the
   current form. If you type the old one in a live-coding round it simply fails.
2. **`pytest-asyncio` ≥ 1.0 removed the `event_loop` fixture.** The famous "redefine `event_loop`
   as a session-scoped fixture to fix *Event loop is closed*" recipe is dead. Use
   `asyncio_mode = "auto"` in config and `@pytest.mark.asyncio(loop_scope=...)` when you need
   control.
3. A third, easy to miss: **`ASGITransport` does not run lifespan events.** Startup code —
   `init_beanie`, connection pools — never executes. Use `TestClient` as a context manager, or
   `LifespanManager` from `asgi-lifespan`. Covered in `09-Testing-And-DevOps/03-async-testing/`.

---

## Follow-ups they will ask next

**"How do you detect this in a running service?"** asyncio debug mode logs callbacks exceeding
`loop.slow_callback_duration`; `py-spy dump --pid` shows what the loop thread is doing right now;
and an event-loop-lag metric is the leading indicator worth putting on a dashboard. See
`02-Async-And-Concurrency/05-blocking-the-loop/`.

**"How many workers should you run?"** `gunicorn -k uvicorn.workers.UvicornWorker -w N`, roughly
one process per core. Workers exist to use multiple cores and isolate crashes — not to provide
concurrency *within* a process, which the loop already does. In Kubernetes, prefer one process per
container and scale with replicas.

**"Does `async` make it faster?"** No — it makes it *scale*. One request is not faster; you serve
far more of them concurrently while they wait on I/O. For CPU-bound work async is marginally
worse.

**"Can you mix them in one app?"** Yes, per endpoint and per dependency, and FastAPI handles each
correctly. That is exactly why the distinction has to be deliberate.

---

## Say it out loud

> FastAPI looks at whether the handler is a coroutine function. An `async def` endpoint is awaited
> directly on the event loop, so a blocking call inside it freezes the entire server — not just
> that request. A plain `def` endpoint is handed to AnyIO's threadpool, so the same blocking call
> only occupies one worker thread and the loop keeps serving everyone else. That means the sync
> version is actually the safer choice when I have to call a synchronous library, which surprises
> people. The caveat is that the threadpool is bounded — forty tokens by default — so under enough
> concurrency requests start queueing for a thread, and the symptom is latency climbing while CPU
> is idle. If a native async client exists I use it and stay on the loop. If I am inside an
> `async def` and need one blocking call, I wrap it in `asyncio.to_thread`. For CPU-bound work
> neither helps: I move it to a process pool or a task queue, because the GIL means a thread still
> starves the loop. The same rule applies to dependencies, which people forget — a `def`
> dependency goes to the threadpool, an `async def` one does not.
