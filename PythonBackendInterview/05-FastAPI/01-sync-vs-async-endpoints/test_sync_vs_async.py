"""Proves the sync-vs-async endpoint claims against a real ASGI app.

Also demonstrates the CURRENT way to test FastAPI asynchronously. Two version notes that matter
because almost every tutorial online is stale:

  * `httpx.AsyncClient(app=app)` was REMOVED in httpx 0.28. Use `ASGITransport(app=app)`.
  * `pytest-asyncio` >= 1.0 REMOVED the `event_loop` fixture. The old "redefine event_loop as a
    session fixture to fix 'Event loop is closed'" recipe no longer works; use `asyncio_mode`
    (set to `auto` in pyproject.toml) and `loop_scope` instead.
"""

from __future__ import annotations

import asyncio
import contextlib
import time

import httpx
import pytest
from sync_vs_async import BLOCK, app

pytestmark = pytest.mark.slow


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _elapsed_for(client: httpx.AsyncClient, path: str, n: int = 4) -> float:
    started = time.perf_counter()
    await asyncio.gather(*(client.get(path) for _ in range(n)))
    return time.perf_counter() - started


async def test_endpoints_all_work(client: httpx.AsyncClient) -> None:
    for path in ["/async-blocking", "/sync-blocking", "/async-proper", "/async-offloaded"]:
        response = await client.get(path)
        assert response.status_code == 200
        assert response.json()["endpoint"] == path.lstrip("/")


async def test_async_def_with_blocking_call_serialises(client: httpx.AsyncClient) -> None:
    """Four concurrent requests take 4x as long, because none of them ever yields."""
    elapsed = await _elapsed_for(client, "/async-blocking", n=4)
    assert elapsed >= BLOCK * 3, (
        f"expected serialisation (~{BLOCK * 4:.2f}s) but got {elapsed:.2f}s"
    )


async def test_plain_def_endpoint_runs_concurrently(client: httpx.AsyncClient) -> None:
    """The same blocking call in a `def` endpoint goes to the threadpool, so it overlaps."""
    elapsed = await _elapsed_for(client, "/sync-blocking", n=4)
    assert elapsed < BLOCK * 2.5, f"expected concurrency (~{BLOCK:.2f}s) but got {elapsed:.2f}s"


async def test_native_async_endpoint_runs_concurrently(client: httpx.AsyncClient) -> None:
    elapsed = await _elapsed_for(client, "/async-proper", n=4)
    assert elapsed < BLOCK * 2.5


async def test_offloading_rescues_an_async_endpoint(client: httpx.AsyncClient) -> None:
    """`asyncio.to_thread` inside `async def` restores concurrency."""
    elapsed = await _elapsed_for(client, "/async-offloaded", n=4)
    assert elapsed < BLOCK * 2.5


async def test_blocking_async_endpoint_starves_the_health_check(client: httpx.AsyncClient) -> None:
    """The damage is not confined to the slow endpoint -- it takes the whole server down."""

    async def count_health_checks(during) -> int:  # noqa: ANN001
        hits = 0
        done = False

        async def poll() -> None:
            nonlocal hits
            while not done:
                await client.get("/health")
                hits += 1
                await asyncio.sleep(0.005)

        task = asyncio.create_task(poll())
        await during()
        done = True
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return hits

    blocked = await count_health_checks(lambda: _elapsed_for(client, "/async-blocking", n=4))
    healthy = await count_health_checks(lambda: _elapsed_for(client, "/sync-blocking", n=4))

    assert blocked <= 3, (
        f"the loop should have been frozen, but {blocked} health checks got through"
    )
    assert healthy > blocked * 3, (
        f"the `def` endpoint should leave the loop free ({healthy} vs {blocked} health checks)"
    )


async def test_threadpool_is_bounded(client: httpx.AsyncClient) -> None:
    """The catch with the `def` answer: AnyIO's limiter has a finite token count (40 by default),
    so enough concurrent blocking endpoints and requests queue waiting for a thread."""
    import anyio.to_thread

    limiter = anyio.to_thread.current_default_thread_limiter()
    total = int(limiter.total_tokens)
    assert total > 0

    elapsed = await _elapsed_for(client, "/sync-blocking", n=total + 20)
    assert elapsed > BLOCK * 1.5, (
        f"more concurrent requests than threads should queue, but it took only {elapsed:.2f}s"
    )
