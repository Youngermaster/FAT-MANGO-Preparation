"""FastAPI dependency injection: caching, yield/teardown, scopes, classes, and overrides.

    uv run python 05-FastAPI/02-dependency-injection/dependencies.py

If you know NestJS, the concept transfers directly -- `Depends` is constructor injection by
another name. What does NOT transfer is the lifecycle: FastAPI dependencies are resolved
per-request and cached per-request, and the `yield` teardown has ordering subtleties that
interviewers like to probe (see `with_background` below, where the behaviour has actually
changed across FastAPI versions).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

# A log the tests read to assert ordering and call counts.
EVENTS: list[str] = []

app = FastAPI(title="dependency injection")


# ==========================================================================================
# 1. Per-request caching -- the behaviour people are surprised by
# ==========================================================================================


def expensive_lookup() -> str:
    """Called ONCE per request no matter how many dependants ask for it.

    FastAPI builds a dependency graph per request and memoises each node by
    `(callable, security_scopes)`. This is why you can decompose dependencies freely without
    worrying that a shared one runs five times.
    """
    EVENTS.append("expensive_lookup")
    return "value"


def dependant_a(value: Annotated[str, Depends(expensive_lookup)]) -> str:
    return f"a:{value}"


def dependant_b(value: Annotated[str, Depends(expensive_lookup)]) -> str:
    return f"b:{value}"


@app.get("/cached")
def cached(
    a: Annotated[str, Depends(dependant_a)],
    b: Annotated[str, Depends(dependant_b)],
) -> dict[str, str]:
    """Two dependants, one shared dependency -> `expensive_lookup` ran exactly once."""
    return {"a": a, "b": b}


def uncached_lookup() -> str:
    EVENTS.append("uncached_lookup")
    return "value"


@app.get("/uncached")
def uncached(
    a: Annotated[str, Depends(uncached_lookup, use_cache=False)],
    b: Annotated[str, Depends(uncached_lookup, use_cache=False)],
) -> dict[str, str]:
    """`use_cache=False` opts out -- for dependencies that must run each time, e.g. one that
    mints a fresh idempotency token or samples a clock."""
    return {"a": a, "b": b}


# ==========================================================================================
# 2. `yield` dependencies -- setup/teardown, and the ordering question
# ==========================================================================================


@dataclass
class FakeSession:
    """Stands in for a DB session / transaction."""

    committed: bool = False
    rolled_back: bool = False
    closed: bool = False
    statements: list[str] = field(default_factory=list)

    def execute(self, sql: str) -> None:
        self.statements.append(sql)


def get_session() -> Iterator[FakeSession]:
    """The canonical transaction dependency: commit on success, roll back on error, always close.

    Everything before `yield` is setup. Everything after runs on the way out -- including when
    the endpoint raised, which is what makes this the right place for a rollback.
    """
    session = FakeSession()
    EVENTS.append("session:open")
    try:
        yield session
        session.committed = True
        EVENTS.append("session:commit")
    except Exception:
        session.rolled_back = True
        EVENTS.append("session:rollback")
        raise  # re-raise so FastAPI still turns it into a response
    finally:
        session.closed = True
        EVENTS.append("session:close")


SessionDep = Annotated[FakeSession, Depends(get_session)]


@app.post("/orders")
def create_order(session: SessionDep) -> dict[str, str]:
    session.execute("INSERT INTO orders ...")
    return {"status": "created"}


@app.post("/orders-failing")
def create_order_failing(session: SessionDep) -> dict[str, str]:
    session.execute("INSERT INTO orders ...")
    raise ValueError("business rule violated")


@app.post("/orders-http-error")
def create_order_http_error(session: SessionDep) -> dict[str, str]:
    """`HTTPException` is still an exception, so the dependency rolls back."""
    session.execute("INSERT INTO orders ...")
    raise HTTPException(status_code=409, detail="duplicate order")


@app.post("/background")
def with_background(session: SessionDep, background: BackgroundTasks) -> dict[str, str]:
    """`yield` dependencies vs BackgroundTasks -- ordering that has CHANGED between versions.

    Verified on the versions pinned in this repo (FastAPI 0.141.1 / Starlette 1.6.0), the order
    is:  open -> handler -> background task -> teardown.  So the session is still open inside
    the task, and `session_closed=False` is what the demo prints.

    History, because an interviewer may have learned a different answer:
      * Before 0.106: teardown ran after the response, so dependencies were usable in tasks.
      * 0.106 changed it -- teardown moved BEFORE the response was sent, so a task that touched
        a `yield` dependency hit an already-closed resource. This was widely written up, and it
        is the version of the story you will find in most blog posts.
      * Current versions put background tasks back before teardown, as asserted in the tests
        next to this file.

    The engineering conclusion does not depend on which version you are on: DO NOT rely on a
    request-scoped resource inside a background task. Acquire what the task needs inside the
    task. That advice is version-proof, and saying so is a better answer than quoting a
    changelog -- especially since the behaviour has flip-flopped.

    And the bigger point: `BackgroundTasks` runs in the same process after the response. If the
    pod dies, the work is simply lost. Anything that must not be lost belongs in a durable queue.
    """

    def task(injected_session: FakeSession) -> None:
        EVENTS.append(f"background:session_closed={injected_session.closed}")

    background.add_task(task, session)
    return {"status": "queued"}


# ==========================================================================================
# 3. Class-based dependencies -- parameterised, and the natural home for RBAC
# ==========================================================================================


class User(BaseModel):
    username: str
    roles: list[str]


def get_current_user(x_user: Annotated[str | None, Header()] = None) -> User:
    """Stand-in for JWT decoding. Real version lives in 07-Auth-Security/."""
    if x_user is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    name, _, roles = x_user.partition(":")
    return User(username=name, roles=roles.split(",") if roles else [])


class RequireRole:
    """A dependency that takes configuration -- expressed as a callable instance.

    `Depends(RequireRole("admin"))` works because FastAPI only needs a callable, and
    `__call__`'s signature is what it introspects for sub-dependencies.
    """

    def __init__(self, role: str) -> None:
        self.role = role

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if self.role not in user.roles:
            raise HTTPException(status_code=403, detail=f"requires role: {self.role}")
        return user


@app.get("/admin")
def admin_only(user: Annotated[User, Depends(RequireRole("admin"))]) -> dict[str, str]:
    return {"hello": user.username}


# ==========================================================================================
# 4. Router- and path-level dependencies that return nothing
# ==========================================================================================


def audit(request: Request) -> None:
    """Pure side effect: no return value, so it is declared on the decorator, not a parameter."""
    EVENTS.append(f"audit:{request.url.path}")


@app.get("/audited", dependencies=[Depends(audit)])
def audited() -> dict[str, bool]:
    return {"ok": True}


# ==========================================================================================
# 5. Settings: cached singleton, still injectable (and therefore still overridable)
# ==========================================================================================


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEMO_")
    app_name: str = "interview-demo"
    page_size: int = 50


@lru_cache
def get_settings() -> Settings:
    """`lru_cache` makes it a singleton -- built once, reused for every request.

    Why inject it instead of importing a module-level instance: tests can override it via
    `app.dependency_overrides[get_settings]`, which a module-level global cannot offer.
    """
    EVENTS.append("settings:constructed")
    return Settings()


@app.get("/config")
def read_config(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, object]:
    return {"app_name": settings.app_name, "page_size": settings.page_size}


# ==========================================================================================
# 6. Reusable parameter bundles
# ==========================================================================================


@dataclass
class Pagination:
    """Validation and defaults in one place, reusable across every list endpoint.

    Note the cap on `limit`: without it, `?limit=1000000` is an unauthenticated way to make your
    database do a lot of work. That is OWASP API4, Unrestricted Resource Consumption.
    """

    limit: int = 50
    offset: int = 0


def pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


@app.get("/items")
def list_items(page: Annotated[Pagination, Depends(pagination)]) -> dict[str, int]:
    return {"limit": page.limit, "offset": page.offset}


# ==========================================================================================
# 7. App-lifetime resources reach request scope via app.state
# ==========================================================================================


async def get_http_client(request: Request) -> AsyncIterator[str]:
    """A connection pool must be created once at startup, not per request.

    The pattern: build it in `lifespan`, stash it on `app.state`, and read it from a dependency.
    See 05-FastAPI/03-lifespan-and-startup/ for the other half.
    """
    yield getattr(request.app.state, "http_client", "<not-initialised>")


@app.get("/client")
async def use_client(client: Annotated[str, Depends(get_http_client)]) -> dict[str, str]:
    return {"client": client}


if __name__ == "__main__":
    from fastapi.testclient import TestClient

    client = TestClient(app)

    def run(label: str, fn) -> None:  # noqa: ANN001
        EVENTS.clear()
        result = fn()
        print(f"\n{label}")
        print(f"  response: {result}")
        print(f"  events:   {EVENTS}")

    run("Per-request cache: one shared dep, two dependants", lambda: client.get("/cached").json())

    run("use_cache=False: runs once per dependant", lambda: client.get("/uncached").json())

    run("yield dependency, happy path -> commit then close", lambda: client.post("/orders").json())

    run(
        "yield dependency, endpoint raised -> rollback then close",
        lambda: client.post("/orders-http-error").status_code,
    )

    run(
        "BackgroundTasks vs yield teardown (ordering verified for THESE versions)",
        lambda: client.post("/background").json(),
    )

    run(
        "class dependency: missing role -> 403",
        lambda: client.get("/admin", headers={"X-User": "bob:reader"}).status_code,
    )

    run(
        "class dependency: has role -> 200",
        lambda: client.get("/admin", headers={"X-User": "alice:admin,reader"}).json(),
    )

    run("dependencies=[...] for pure side effects", lambda: client.get("/audited").json())

    run(
        "settings singleton is built once, then cached",
        lambda: [client.get("/config").json(), client.get("/config").json()][0],
    )

    run(
        "pagination bundle rejects an over-large limit",
        lambda: client.get("/items", params={"limit": 100000}).status_code,
    )

    # Overriding a dependency -- the reason to inject settings rather than import them.
    app.dependency_overrides[get_settings] = lambda: Settings(app_name="overridden", page_size=1)
    run("dependency_overrides swaps settings in tests", lambda: client.get("/config").json())
    app.dependency_overrides.clear()
