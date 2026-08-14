# Dependency Injection

> **Prompt as you will hear it:** *"Explain `Depends`. How would you inject a database session and
> make sure it always closes?"*

If you know NestJS, the *concept* transfers directly — `Depends` is constructor injection by
another name. What does not transfer is the **lifecycle**: FastAPI resolves and caches
dependencies **per request**, and the `yield` teardown has ordering subtleties worth knowing.

---

## Run it

```bash
uv run python 05-FastAPI/02-dependency-injection/dependencies.py
uv run pytest 05-FastAPI/02-dependency-injection
```

---

## 1. Per-request caching (the surprising one)

```python
@app.get("/cached")
def cached(a=Depends(dependant_a), b=Depends(dependant_b)):  # both need expensive_lookup
    ...


# expensive_lookup ran ONCE
```

FastAPI builds a dependency graph per request and memoises each node by
`(callable, security_scopes)`. So you can decompose dependencies freely — `get_current_user` used
by six sub-dependencies decodes the JWT once.

The cache is **per request**, not per app: two requests run it twice. Opt out with
`Depends(fn, use_cache=False)` when the dependency must run each time (minting an idempotency
token, sampling a clock).

---

## 2. `yield` dependencies — setup and teardown

```python
def get_session():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise  # re-raise so FastAPI still builds a response
    finally:
        session.close()
```

Everything before `yield` is setup; everything after runs on the way out — **including when the
endpoint raised**, which is what makes this the right home for a rollback.

Note `HTTPException` is an exception like any other here: raising a 409 rolls back. Tested.

### The BackgroundTasks ordering — and why the honest answer is better than the changelog

This has **changed between FastAPI versions**, and you may meet an interviewer who learned a
different answer than yours:

| Version | Order |
|---|---|
| before 0.106 | teardown ran after the response — dependencies usable in tasks |
| 0.106 | teardown moved **before** the response — using a `yield` dep in a task hit a closed resource |
| current (0.141.1 here) | background task runs **before** teardown again — the session is still open |

The last row is not remembered, it is **asserted** by
`test_teardown_ordering_relative_to_background_tasks`, so an upgrade that flips it fails the suite
instead of silently making this README wrong.

The version-proof answer, and the one to give:

> **Don't rely on a request-scoped resource inside a background task — acquire what the task needs
> inside the task.** And `BackgroundTasks` runs in-process after the response, so if the pod dies
> the work is lost. Anything that must not be lost belongs in a durable queue (ARQ, Celery, SQS).

Naming that the behaviour has flip-flopped is a stronger answer than confidently quoting one
version, because it shows you know why the guidance exists.

---

## 3. Class-based dependencies — parameterised injection

```python
class RequireRole:
    def __init__(self, role):
        self.role = role

    def __call__(self, user=Depends(get_current_user)):
        if self.role not in user.roles:
            raise HTTPException(403)
        return user


@app.get("/admin")
def admin(user=Depends(RequireRole("admin"))): ...
```

FastAPI only needs a **callable**; it introspects `__call__`'s signature for sub-dependencies. This
is the idiomatic way to build configurable dependencies, and the natural home for RBAC.

---

## 4. Dependencies that return nothing

For pure side effects (audit logging, rate limiting, an auth check whose result you don't need),
declare them on the decorator instead of as a parameter:

```python
@app.get("/audited", dependencies=[Depends(audit)])
```

Also available at router level (`APIRouter(dependencies=[...])`) and app level — the usual place
to enforce authentication across a whole router.

---

## 5. Why inject settings instead of importing them

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()


@app.get("/config")
def config(settings=Depends(get_settings)): ...
```

`lru_cache` makes it a singleton — built once, reused everywhere. But it is still a *dependency*,
so tests can swap it:

```python
app.dependency_overrides[get_settings] = lambda: Settings(app_name="test")
```

**`dependency_overrides` beats monkeypatching**, and this is worth saying explicitly: it replaces
the node in the graph rather than reaching into another module's namespace, so there are no
import-order surprises and it is scoped to the app object. A module-level global cannot offer
that. This is the single most useful FastAPI testing feature.

---

## 6. Middleware vs dependencies

A near-certain follow-up:

| Use a **dependency** when | Use **middleware** when |
|---|---|
| You need parsed, typed, validated input | You operate on the raw request/response |
| You want to short-circuit with a proper 4xx | It is genuinely global (CORS, GZip, request-ID, tracing) |
| It should appear in the OpenAPI schema | It must run even for unmatched routes / 404s |
| You want per-route granularity | You need to time or wrap the whole cycle |

The schema point is concrete and testable: query parameters declared in a dependency show up in
`/openapi.json`, so generated clients know about them. Middleware is invisible to the schema —
`test_dependencies_appear_in_the_openapi_schema` demonstrates it.

Also worth knowing: `BaseHTTPMiddleware` cannot easily read a response body and interferes with
streaming responses; pure ASGI middleware is the escape hatch.

---

## 7. App-lifetime resources

A connection pool must be created **once at startup**, not per request. The pattern is:

```python
# lifespan:      app.state.mongo = AsyncMongoClient(...)
# dependency:    def get_db(request: Request): return request.app.state.mongo
```

Creating a client per request is the classic performance bug — you lose pooling entirely. See
`05-FastAPI/03-lifespan-and-startup/`.

---

## A current-versions note

Running the tests surfaces `StarletteDeprecationWarning: Using httpx with starlette.testclient is
deprecated; install httpx2 instead`. Worth a mention if testing comes up — it signals you actually
run this stack rather than recite it. `TestClient` remains the right tool when you need lifespan
events; `httpx.AsyncClient` + `ASGITransport` is the async path (and does **not** run lifespan).

---

## Follow-ups they will ask next

**"Is a dependency a singleton?"** No — per request, cached within that request. Use `lru_cache`
on the provider (or `app.state` from lifespan) for genuine app-lifetime singletons.

**"Sync or async dependency?"** Same rule as endpoints: a `def` dependency goes to the threadpool,
an `async def` one runs on the loop. Blocking inside an `async def` dependency freezes the server
exactly as it would in an endpoint.

**"How do you test an endpoint that needs auth?"** Override the auth dependency:
`app.dependency_overrides[get_current_user] = lambda: User(...)`. No token minting, no mocking
`jwt.decode`.

**"How deep can dependencies nest?"** Arbitrarily — it is a DAG, resolved depth-first with caching.
Circular dependencies are a startup error.

---

## Say it out loud

> `Depends` is FastAPI's DI: you declare what a handler needs and FastAPI resolves the graph per
> request, caching each node so a shared dependency like `get_current_user` runs once even if six
> things depend on it — and I can opt out with `use_cache=False`. For a database session I use a
> `yield` dependency: setup before the yield, commit after it, rollback in an `except` with a
> re-raise, and close in a `finally`. That gives me guaranteed teardown even when the endpoint
> raises, including `HTTPException`. One thing I am careful about is background tasks — the
> ordering relative to `yield` teardown has actually changed across FastAPI versions, so I never
> rely on a request-scoped resource inside a task; I acquire what the task needs inside the task.
> And `BackgroundTasks` is in-process, so anything that must survive a pod restart goes to a real
> queue. For configuration I wrap settings in `lru_cache` so it is a singleton but still
> injectable, which means tests can replace it through `dependency_overrides` — that is much
> better than monkeypatching, because it swaps the node in the graph instead of reaching into
> another module. I use dependencies rather than middleware whenever I need typed input, a proper
> 4xx, or the parameters to appear in the OpenAPI schema; middleware is for genuinely global
> concerns like CORS and request IDs.
