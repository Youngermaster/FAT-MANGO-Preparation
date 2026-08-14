"""Pins FastAPI's dependency-injection semantics so nothing here is claimed from memory."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from dependencies import EVENTS, Settings, app, get_settings
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    EVENTS.clear()
    yield
    EVENTS.clear()
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------------------------------------
# Per-request caching
# ------------------------------------------------------------------------------------------


def test_shared_dependency_runs_once_per_request(client: TestClient) -> None:
    response = client.get("/cached")
    assert response.status_code == 200
    assert EVENTS.count("expensive_lookup") == 1, "FastAPI caches each dependency per request"


def test_cache_does_not_persist_across_requests(client: TestClient) -> None:
    client.get("/cached")
    client.get("/cached")
    assert EVENTS.count("expensive_lookup") == 2, "the cache is per-request, not per-app"


def test_use_cache_false_opts_out(client: TestClient) -> None:
    client.get("/uncached")
    assert EVENTS.count("uncached_lookup") == 2


# ------------------------------------------------------------------------------------------
# yield dependencies
# ------------------------------------------------------------------------------------------


def test_yield_dependency_commits_on_success(client: TestClient) -> None:
    assert client.post("/orders").status_code == 200
    assert EVENTS == ["session:open", "session:commit", "session:close"]


def test_yield_dependency_rolls_back_when_the_endpoint_raises(client: TestClient) -> None:
    with pytest.raises(ValueError):
        client.post("/orders-failing")
    assert EVENTS == ["session:open", "session:rollback", "session:close"]


def test_http_exception_also_triggers_rollback(client: TestClient) -> None:
    """`HTTPException` is an exception like any other as far as the dependency is concerned."""
    response = client.post("/orders-http-error")
    assert response.status_code == 409
    assert EVENTS == ["session:open", "session:rollback", "session:close"]


def test_teardown_ordering_relative_to_background_tasks(client: TestClient) -> None:
    """Pins the ordering that has changed between FastAPI versions.

    On the versions pinned in this repo the background task runs BEFORE the dependency's
    teardown, so the injected session is still open. If a future upgrade flips this back, this
    test fails loudly instead of the README quietly becoming wrong.

    Either way the guidance stands: do not use a request-scoped resource in a background task.
    """
    assert client.post("/background").status_code == 200
    assert EVENTS == [
        "session:open",
        "background:session_closed=False",
        "session:commit",
        "session:close",
    ]


# ------------------------------------------------------------------------------------------
# Class-based dependencies / authorisation
# ------------------------------------------------------------------------------------------


def test_missing_credentials_gives_401(client: TestClient) -> None:
    assert client.get("/admin").status_code == 401


def test_wrong_role_gives_403(client: TestClient) -> None:
    assert client.get("/admin", headers={"X-User": "bob:reader"}).status_code == 403


def test_correct_role_passes(client: TestClient) -> None:
    response = client.get("/admin", headers={"X-User": "alice:admin,reader"})
    assert response.status_code == 200
    assert response.json() == {"hello": "alice"}


def test_route_level_dependency_runs_for_side_effects(client: TestClient) -> None:
    assert client.get("/audited").json() == {"ok": True}
    assert "audit:/audited" in EVENTS


# ------------------------------------------------------------------------------------------
# Settings and overrides
# ------------------------------------------------------------------------------------------


def test_settings_are_constructed_once(client: TestClient) -> None:
    get_settings.cache_clear()
    EVENTS.clear()
    client.get("/config")
    client.get("/config")
    client.get("/config")
    assert EVENTS.count("settings:constructed") == 1, "lru_cache makes it a singleton"


def test_dependency_override_replaces_settings(client: TestClient) -> None:
    """The reason to inject settings rather than import a module-level global: this.

    `dependency_overrides` beats monkeypatching because it swaps the node in the graph rather
    than reaching into another module's namespace -- no import-order surprises, and it is
    automatically scoped to the app object.
    """
    app.dependency_overrides[get_settings] = lambda: Settings(app_name="test", page_size=1)
    assert client.get("/config").json() == {"app_name": "test", "page_size": 1}

    app.dependency_overrides.clear()
    assert client.get("/config").json()["app_name"] == "interview-demo"


# ------------------------------------------------------------------------------------------
# Parameter bundles
# ------------------------------------------------------------------------------------------


def test_pagination_defaults(client: TestClient) -> None:
    assert client.get("/items").json() == {"limit": 50, "offset": 0}


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_pagination_rejects_out_of_range(client: TestClient, params: dict[str, int]) -> None:
    """The cap matters: an uncapped `limit` is OWASP API4, Unrestricted Resource Consumption."""
    assert client.get("/items", params=params).status_code == 422


def test_dependencies_appear_in_the_openapi_schema(client: TestClient) -> None:
    """A real advantage of dependencies over middleware: they are part of the contract.

    Query parameters declared in a dependency show up in `/openapi.json`, so generated clients
    and the docs page know about them. Middleware is invisible to the schema.
    """
    schema = client.get("/openapi.json").json()
    params = schema["paths"]["/items"]["get"]["parameters"]
    names = {p["name"] for p in params}
    assert {"limit", "offset"} <= names
