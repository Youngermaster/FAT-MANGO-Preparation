# Rapid-Fire Q&A

Short spoken answers — the length you would actually say out loud, not an essay. Cover the right
column and drill.

Answers marked **⚠️** are ones where the common/older answer is now wrong. Those are the highest
value per second: they cost nothing to learn and they signal you work with current versions.

---

## Language core

| Question | Answer |
|---|---|
| `is` vs `==`? | Identity vs value. Use `is` only for `None`, booleans and sentinels. Small ints and compile-time string literals are cached, which makes `is` accidentally work and teaches people the wrong lesson. |
| Mutable default argument? | Defaults are evaluated once, at `def` time, so the object is shared by every call. Use a `None` sentinel. You can see it in `func.__defaults__`. |
| Why does `[lambda: i for i in range(5)]` return all 4s? | Closures are late-binding — they capture the variable, not the value. Bind with a default arg or `functools.partial`. Ruff's B023 catches it. |
| Shallow vs deep copy? | Shallow duplicates the outer container and shares the inner objects. `dict.copy()` does not protect nested config. `deepcopy` walks the whole graph and is slow. |
| What can be a dict key? | Anything hashable — effectively immutable. `list`/`dict`/`set` cannot. Mutating a key would strand it in the wrong bucket. |
| `__str__` vs `__repr__`? | `__repr__` is for developers and should be unambiguous; `__str__` is for users. If you define only one, define `__repr__` — it is the fallback. |
| What is `__slots__`? | Replaces the per-instance `__dict__` with a fixed layout: ~40–50% less memory and slightly faster attribute access. You lose dynamic attributes and (unless declared) weakrefs. |
| `@staticmethod` vs `@classmethod`? | `classmethod` gets the class and is the idiom for alternative constructors; `staticmethod` gets nothing and is just a namespaced function. Both are descriptors. |
| What is a descriptor? | An object defining `__get__`/`__set__`/`__delete__`, used for attribute access. `property`, `classmethod`, `staticmethod` and ORM fields are all descriptors. Data descriptors take precedence over the instance `__dict__`. |
| What is the MRO? | The linearised order Python searches for attributes, computed by C3. It is what makes cooperative `super()` work in multiple inheritance. `Class.__mro__` shows it. |
| When would you use a metaclass? | Almost never. `__init_subclass__` and `__set_name__` cover most real cases. Knowing to say "last resort" is the answer. |
| ABC vs `Protocol`? | ABC is nominal — you must inherit. `Protocol` is structural — matching shape is enough, checked statically. Protocol suits duck-typed code and avoids inheritance coupling. |
| Generator vs list comprehension? | A generator is lazy and O(1) memory; a list is eager and O(n). Generators are single-use — that is the trap when you return one from an API. |
| What does `yield from` do? | Delegates to a sub-iterator, forwarding values, `send`, and exceptions. Flattens nested generator plumbing. |
| Context manager? | `__enter__`/`__exit__`, or `@contextlib.contextmanager` over a generator. Guarantees cleanup on every path. Returning `True` from `__exit__` **suppresses** the exception. |
| Decorator with arguments? | Three layers: a function returning a decorator returning a wrapper. Always `functools.wraps` the inner one or you lose `__name__`, the docstring and the signature. |
| `dataclass` vs Pydantic vs attrs? | Dataclass: stdlib, no validation, cheap — use internally. Pydantic v2: Rust core, validation and serialisation — use at trust boundaries (HTTP, config, message payloads). attrs: validators/converters, often the fastest with slots. |
| What is `functools.lru_cache`'s trap? | Arguments must be hashable; `maxsize=None` is unbounded (a memory leak); and decorating a **method** keeps `self` in the key, pinning every instance in memory. |
| ⚠️ `sys.getrefcount(1)` returns 4294967295? | That is the **immortal object** sentinel (PEP 683, 3.12), not a count. Refcounts are never updated for small ints, `None`, booleans. It is groundwork for per-interpreter GIL and free-threading. |
| How does Python manage memory? | Reference counting primarily, plus a generational cyclic GC for reference cycles. `gc.collect()` forces it; `weakref` avoids keeping things alive. |
| Common memory-leak shapes? | Unbounded caches (`lru_cache(maxsize=None)`), module-level globals, closures capturing large objects, long-lived asyncio tasks holding references, logging handlers. |
| How do you profile? | `cProfile`/`py-spy` for CPU, `tracemalloc`/`memray` for allocations, `timeit` for microbenchmarks. `py-spy dump --pid` works on a live process without restarting it. |
| `Optional[X]` in Pydantic v2? | ⚠️ It no longer implies a default of `None` — the field is **required unless you give one**. Silent breakage when migrating from v1. |

---

## Async

| Question | Answer |
|---|---|
| What is the event loop? | One thread running one callback at a time, with a ready queue, a heap of scheduled callbacks, and a selector (`epoll`/`kqueue`) for I/O readiness. |
| Sync vs async, in one line? | Async is cooperative multitasking on a single thread. A coroutine holds the thread until it hits an `await` that actually suspends. |
| `time.sleep` vs `asyncio.sleep`? | `time.sleep` parks the thread and freezes the loop. `asyncio.sleep` yields to the loop. The most-confused pair in Python. |
| Blocking call in an `async def` endpoint? | It freezes the whole server — every request, the health check, background tasks. |
| ...and in a plain `def` endpoint? | Starlette runs it in AnyIO's threadpool, so it costs one worker thread. **The sync endpoint is safer for blocking work.** The pool is bounded (40 tokens), so enough of them and requests queue. |
| Coroutine vs Task vs Future? | A coroutine is inert until awaited. A Task is a Future subclass that drives a coroutine on the loop — that is what creates concurrency. A Future is a low-level result placeholder, usually bridging callback APIs. |
| `gather` vs `TaskGroup`? | `gather` raises the first exception but does **not** cancel siblings — they keep running after you have handled the error. `TaskGroup` cancels siblings and raises an `ExceptionGroup` that can carry several failures. TaskGroup is my default. |
| When `gather(return_exceptions=True)`? | Best-effort fan-out where one failure should not abort the rest. Remember to filter results for exception instances. |
| `as_completed`? | Yields in completion order — good for streaming or first-good-answer. It will **not** cancel the losers for you. |
| `asyncio.wait` gotcha? | It neither raises nor cancels. You must cancel `pending` yourself and inspect `done` for exceptions. Since 3.12 it takes Tasks, not coroutines. |
| How do you cancel? | `task.cancel()` requests it; `CancelledError` is raised at the next await point. Since 3.8 it inherits `BaseException`, so `except Exception` will not swallow it — but `except BaseException` will, which makes the task uncancellable. Catch it for cleanup, then **re-raise**. |
| Timeouts? | `async with asyncio.timeout(n)` (3.11+) over `wait_for` — it composes as a context manager, wraps a whole block, and uses cancel-counting so nested timeouts attribute correctly. |
| Limit concurrency to 10? | `asyncio.Semaphore(10)` acquired **inside** each worker, then gather. Around the gather instead and it silently serialises. For huge or streaming input, a worker pool over an `asyncio.Queue` with `maxsize` for backpressure. |
| Why not unbounded `gather`? | 10,000 sockets at once: exhausts the connection pool, hits the fd limit, and DDoSes the dependency. |
| `create_task` hazard? | The loop holds only a weak reference — keep a strong one in a set with `add_done_callback(discard)`, or the task can be GC'd mid-flight and exceptions vanish. |
| `to_thread` vs `run_in_executor`? | `to_thread` is the ergonomic wrapper over the default thread pool. `run_in_executor` when you need a specific pool — above all a `ProcessPoolExecutor`, which `to_thread` cannot give you. |
| How do you find a blocked loop in prod? | asyncio debug mode logs slow callbacks; `py-spy dump --pid`; an event-loop-lag metric. The symptom is p99 collapsing under load while CPU is idle. |
| Does `async` make code faster? | No — it makes it *scale* under I/O concurrency. One request is not faster. For CPU-bound work it is marginally worse. |

---

## Concurrency and the GIL

| Question | Answer |
|---|---|
| What is the GIL? | A mutex letting one thread execute Python bytecode at a time. It protects reference counts. **Never say "Python can't do threads"** — it limits *parallelism* for CPU-bound work, not concurrency. |
| When does the GIL not matter? | During I/O (it is released while waiting) and inside GIL-releasing C extensions — numpy, zlib, `ssl`, image codecs. |
| asyncio vs threads vs processes? | asyncio for high-concurrency I/O; threads for blocking I/O with sync-only libraries; processes for CPU-bound. Or sidestep with a C extension. |
| Is `x += 1` atomic? | No. It compiles to load, add, store — `dis` shows it. Two threads can interleave. The GIL never made your code correct, only lucky. |
| ⚠️ Free-threaded Python? | PEP 703 adds a build without the GIL (`python3.14t`). PEP 779 made it **officially supported in 3.14**. Costs ~5–10% single-thread performance and more memory; ABI-incompatible, so C extensions need `cp314t` wheels. GIL-off-by-default is expected around 2027–28. |
| `fork` vs `spawn`? | `fork` is fast but unsafe with threads or an active event loop; `spawn` is safe and slower. ⚠️ 3.14 changed the Linux default to `forkserver`. |
| Is `asyncio.Semaphore` thread-safe? | No. asyncio primitives assume one loop on one thread. Use `threading.Semaphore` across threads and never `await` a threading primitive. |

---

## FastAPI

| Question | Answer |
|---|---|
| `Depends` in one line? | Declarative DI: FastAPI resolves a dependency graph per request and caches each node within that request, so a shared dependency runs once. |
| Is a dependency a singleton? | No — per request. Use `lru_cache` on the provider or `app.state` from lifespan for app-lifetime objects. |
| `yield` dependency? | Setup before the yield, teardown after — and the teardown runs even when the endpoint raised, which is why it is the right home for a transaction rollback. |
| Dependencies in background tasks? | Don't rely on them. The ordering relative to `yield` teardown has changed across FastAPI versions. Acquire what the task needs inside the task. |
| ⚠️ `@app.on_event("startup")`? | Deprecated since 0.93. Use the `lifespan` async context manager — it composes and handles exceptions properly. Mixing both makes `on_event` silently not fire. |
| `BackgroundTasks` vs Celery/ARQ? | `BackgroundTasks` runs in-process after the response — fine for short, idempotent, loss-tolerant work. If the pod dies the work is gone. Use ARQ for an all-async stack, Celery for broad broker/ecosystem needs. |
| Middleware vs dependency? | Dependency when you need typed input, a proper 4xx, per-route granularity, or it to appear in OpenAPI. Middleware for genuinely global concerns — CORS, GZip, request IDs, tracing — and it is invisible to the schema. |
| How do you test with auth? | `app.dependency_overrides[get_current_user] = lambda: User(...)`. Better than monkeypatching: it swaps the node in the graph, no import-order surprises. |
| ⚠️ Async test client? | `httpx.AsyncClient(transport=ASGITransport(app=app))`. The `AsyncClient(app=app)` shortcut was **removed in httpx 0.28**. |
| ⚠️ Does `ASGITransport` run lifespan? | **No.** Startup code like `init_beanie` never runs. Use `TestClient` as a context manager, or `LifespanManager` from `asgi-lifespan`. |
| ⚠️ `pytest-asyncio` event loop? | The `event_loop` fixture was **removed in 1.0**. The old "redefine it as a session fixture" recipe is dead — use `asyncio_mode = "auto"` and `loop_scope`. |
| `response_model` cost? | An extra validation pass. For hot endpoints returning pre-serialised data, return an `ORJSONResponse` directly and skip it. |
| Why separate Create/Read/InDB models? | So you never leak internal fields, and so clients cannot set fields they shouldn't (mass assignment — OWASP API3). `extra="forbid"` helps. |
| Cursor vs offset pagination? | `skip(n)` makes the server walk and discard n rows, so deep pages degrade — and worse, insertions mid-scroll cause duplicates and gaps. Keyset anchors on the last seen value. |
| How many workers? | `gunicorn -k uvicorn.workers.UvicornWorker`, roughly one process per core. Workers are for using cores and isolating crashes, not for concurrency within a request. |

---

## MongoDB / Beanie

| Question | Answer |
|---|---|
| ⚠️ Which async driver? | `pymongo.AsyncMongoClient`. Motor was deprecated 2026-05-14. PyMongo Async is natively asyncio rather than delegating to a thread pool, so it is lower-latency. Beanie 2.0 dropped Motor too. |
| Embed or reference? | Embed when owned by the parent, always read together, and **bounded**. Reference when large, independently queried, shared, or unbounded — because of the 16 MB document limit and the unbounded-array anti-pattern. |
| Compound index field order? | **ESR**: Equality, then Sort, then Range. Verify with `explain` — you want `IXSCAN` and no blocking `SORT` stage. |
| Index prefix rule? | An index on `{a,b,c}` serves `{a}`, `{a,b}`, `{a,b,c}` — not `{b}` alone. One good compound index often replaces three. |
| Covered query? | Answered entirely from the index; `totalDocsExamined: 0`. Needs the projection to stay within indexed fields. |
| Reading `explain`? | `nReturned` ≈ `totalKeysExamined` is healthy. Docs examined ≫ returned means a weak index. A `SORT` stage means a missing one. |
| Aggregation performance rule? | `$match` first — only a leading `$match` can use an index. Blocking stages have a 100 MB limit unless `allowDiskUse`. |
| Results plus a total count? | `$facet` — both in one round trip. |
| Transactions? | Single-document writes are always atomic. Multi-document transactions need a replica set, have a 60s default limit, and do not scale like single-doc writes. Prefer to design them away by embedding what must change together. |
| Claim a row exactly once without a transaction? | Optimistic update: put the expected state in the **filter**, and check `modified_count == 1`. Ten concurrent claimers, one winner, one round trip. |
| Where does `init_beanie` go? | In `lifespan`, once per process. With N workers it runs N times — index creation is idempotent, but for large collections build indexes in a migration so boot does not stall a rollout. |
| Mongo N+1? | `fetch_links=True` on a list endpoint issues a `$lookup` per document. Fix with a `$lookup` you control, a batched `$in`, or denormalising the two fields you display. |
| ⚠️ Money in Beanie? | `DecimalAnnotation`, not `Decimal` — BSON stores `Decimal128` and plain Pydantic `Decimal` **fails on read**. Never `float`. |
| Shard key choice? | High cardinality, high query frequency, and **non-monotonic** — a timestamp key sends every write to one shard. |

---

## Auth and security

| Question | Answer |
|---|---|
| OAuth2 vs OIDC? | OAuth 2.0 is authorisation — delegated access. OIDC is a thin identity layer on top that adds the **ID token**. |
| Which token does an API validate? | The **access token**. Never accept an ID token as an API credential. |
| Which flow for an SPA or mobile app? | Authorization Code **with PKCE**. ⚠️ OAuth 2.1 removed the implicit and password grants — proposing implicit is a red flag. |
| What does PKCE solve? | Public clients cannot keep a secret. The client sends `S256(verifier)` up front and the verifier at token exchange, so an intercepted authorization code is useless. |
| `state` vs `nonce`? | `state` prevents CSRF on the redirect; `nonce` prevents token replay/substitution. Different jobs, both required. |
| JWT validation checklist? | Signature; `alg` against an **allow-list**; `iss`; `aud`; `exp`/`nbf` with clock skew; `kid` → JWKS with caching and rotation. |
| JWT attacks to name? | `alg: none`; algorithm confusion (RS256 token verified as HS256 using the public key as the HMAC secret); missing `aud` letting a token replay across services; weak HMAC secrets. |
| HS256 or RS256? | Asymmetric for microservices — only the auth server can mint, every service verifies with the public JWKS. |
| Can you revoke a JWT? | Not natively — that is the trade-off for being stateless. Mitigate with short TTLs, a `jti` denylist in Redis, a `token_version` claim, or reference tokens with introspection. |
| Where do you store tokens? | Not `localStorage` (XSS-readable). Access token in memory, refresh token in an `HttpOnly`, `Secure`, `SameSite` cookie, with rotation and reuse detection. |
| Scopes vs roles? | Scopes are what the *client app* may request; roles/permissions are what the *user* may do. Roles in the JWT go stale until expiry — a real trade-off to name. |
| Biggest real-world API bug? | **BOLA** (OWASP API1) — a valid token is not authorisation for *that object*. Always check the resource belongs to the caller. |
| Hashing passwords? | argon2 (or bcrypt). ⚠️ `passlib` is effectively unmaintained; prefer `pwdlib`/`argon2-cffi`. Similarly `pyjwt` over `python-jose`. |

---

## Testing, architecture, ops

| Question | Answer |
|---|---|
| pytest fixture scopes? | function, class, module, package, session, plus `autouse`. `conftest.py` shares them down the tree. |
| Mock vs fake vs stub? | Stub returns canned data, fake is a working lightweight implementation, mock asserts on interactions. "Don't mock what you don't own" — wrap third-party clients and fake the wrapper. |
| Mock Mongo or run it? | Run it. `mongomock` does not implement real index behaviour, the full aggregation language, or transactions — exactly what is worth testing. Testcontainers or Compose, with a fresh database per test. |
| Idempotency? | An idempotency key plus a dedup table, so a retried request is safe. At-least-once delivery with an idempotent consumer is the practical version of exactly-once. |
| Retry storm? | Exponential backoff **with jitter**, retry budgets, and a circuit breaker so retries do not amplify load exactly when the system can least afford it. |
| Retry vs circuit breaker? | Retry is per-call and optimistic. A breaker is per-dependency and has memory — after N failures it stops calling entirely and fails fast. They compose: breaker outside, retry inside. |
| Cache stampede? | Many concurrent misses on the same hot key hammer the database. Fix with a lock/singleflight, early recomputation, or TTL jitter so keys do not expire together. |
| Deployment strategies? | Rolling (default, gradual), blue-green (two environments, instant switch and rollback), canary (small traffic percentage first, watch metrics). Pair with expand/contract migrations so each step is independently deployable. |
| Zero-downtime schema change? | Expand/contract: add the new field, backfill, dual-write, switch reads, drop the old field. Never a single breaking migration. |
| Observability? | Structured logs with a correlation ID, OpenTelemetry traces, RED metrics (rate, errors, duration) and SLOs. A trace ID that spans services is what makes a distributed bug tractable. |
| Microservices or a modular monolith? | Start with a modular monolith. Split when you need independent scaling, independent deploys, or team autonomy — not for tidiness. Distributed systems trade local calls for network failures. |
| Docker image for Python? | Multi-stage, `python:3.13-slim` (not Alpine — musl breaks wheels), `uv sync --frozen --no-dev`, non-root user, dependency layer before source for caching, no secrets in `ENV`. |
| Graceful shutdown? | SIGTERM → stop accepting new requests → drain in-flight → close pools. Needs the exec form of `CMD` so the signal reaches the process, and a `preStop` hook plus `terminationGracePeriodSeconds` in Kubernetes. |
| ⚠️ Modern tooling? | `ruff` (replaces black + isort + flake8), `uv` (replaces pip/poetry/pyenv for most work), mypy or pyright, pre-commit, `pip-audit`. |

---

## Questions to ask them

Worth having two or three ready — it reads as engagement, not filler.

- What does the team's current biggest technical challenge look like?
- How is the backend split — modular monolith, microservices? How do services talk to each other?
- What does the testing and deployment pipeline look like today?
- How does the team actually use AI-assisted development, and what has worked or not worked?
- What would a successful first three months look like in this role?
