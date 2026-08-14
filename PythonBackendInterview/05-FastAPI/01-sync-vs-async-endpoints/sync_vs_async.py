"""`def` vs `async def` endpoints in FastAPI -- and why the sync one is sometimes safer.

    uv run python 05-FastAPI/01-sync-vs-async-endpoints/sync_vs_async.py

This is the FastAPI question with the highest chance of being asked, and the answer is
counter-intuitive enough that most candidates get it backwards.

The short version:

    async def endpoint  -> runs ON the event loop      -> a blocking call freezes the SERVER
    def       endpoint  -> runs in AnyIO's THREADPOOL  -> a blocking call costs ONE thread

So if you must call a synchronous library, declaring the endpoint `def` is the CORRECT answer,
not a fallback.
"""

from __future__ import annotations

import asyncio
import contextlib
import time

import anyio.to_thread
from fastapi import FastAPI

app = FastAPI(title="sync vs async endpoints")

BLOCK = 0.25


@app.get("/async-blocking")
async def async_blocking() -> dict[str, str]:
    """THE BUG. `async def` runs on the loop; `time.sleep` never yields.

    While this is executing, the entire server is frozen -- every other request, the health
    endpoint, background tasks, all of it.
    """
    time.sleep(BLOCK)
    return {"endpoint": "async-blocking"}


@app.get("/sync-blocking")
def sync_blocking() -> dict[str, str]:
    """Same blocking call, but a plain `def`.

    Starlette sees a non-coroutine function and runs it in AnyIO's threadpool via
    `run_in_threadpool`. The loop keeps serving everything else; this costs one worker thread.
    """
    time.sleep(BLOCK)
    return {"endpoint": "sync-blocking"}


@app.get("/async-proper")
async def async_proper() -> dict[str, str]:
    """The good case: genuinely async work, awaited."""
    await asyncio.sleep(BLOCK)
    return {"endpoint": "async-proper"}


@app.get("/async-offloaded")
async def async_offloaded() -> dict[str, str]:
    """`async def` that must call a blocking library: push it to a thread explicitly."""
    await asyncio.to_thread(time.sleep, BLOCK)
    return {"endpoint": "async-offloaded"}


@app.get("/health")
async def health() -> dict[str, bool]:
    """Cheap endpoint used to measure whether the server is still responsive."""
    return {"ok": True}


# ==========================================================================================
# Dependencies follow exactly the same rule
# ==========================================================================================


def sync_dependency() -> str:
    """A `def` dependency also goes to the threadpool."""
    time.sleep(0.01)
    return "sync-dep"


async def async_dependency() -> str:
    """An `async def` dependency runs on the loop -- blocking in here is just as fatal."""
    await asyncio.sleep(0.01)
    return "async-dep"


# ==========================================================================================
# Demo: measure how each endpoint affects everyone else
# ==========================================================================================


async def _measure(client, path: str, concurrent: int = 4) -> tuple[float, int]:  # noqa: ANN001
    """Fire `concurrent` requests at `path` while hammering /health, return (elapsed, health_hits)."""
    health_hits = 0
    stop = False

    async def health_poller() -> None:
        nonlocal health_hits
        while not stop:
            try:
                await client.get("/health", timeout=5.0)
                health_hits += 1
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(0.005)

    poller = asyncio.create_task(health_poller())
    started = time.perf_counter()
    await asyncio.gather(*(client.get(path) for _ in range(concurrent)))
    elapsed = time.perf_counter() - started
    stop = True
    poller.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await poller
    return elapsed, health_hits


async def main() -> None:
    import httpx

    transport = httpx.ASGITransport(app=app)
    # NOTE: `AsyncClient(app=app)` was REMOVED in httpx 0.28. Passing an explicit ASGITransport
    # is the current way, and getting this right is itself a small signal that you are working
    # against today's versions rather than a 2023 tutorial.
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print(f"\n4 concurrent requests, each doing {BLOCK}s of work.")
        print("'/health hits' = how many health checks got served meanwhile.\n")
        print(f"  {'endpoint':<20} {'total':>7}  {'health hits':>11}   verdict")
        print(f"  {'-' * 20} {'-' * 7}  {'-' * 11}   {'-' * 30}")

        for path, note in [
            ("/async-blocking", "serialised AND froze the loop"),
            ("/sync-blocking", "threadpool: concurrent, loop free"),
            ("/async-proper", "native async: concurrent, loop free"),
            ("/async-offloaded", "to_thread: concurrent, loop free"),
        ]:
            elapsed, hits = await _measure(client, path)
            print(f"  {path:<20} {elapsed:6.2f}s  {hits:>11}   {note}")

        print(
            f"\n  Ideal total for 4 concurrent {BLOCK}s requests is ~{BLOCK:.2f}s.\n"
            f"  /async-blocking takes ~{BLOCK * 4:.2f}s because the requests SERIALISE,\n"
            f"  and serves ~0 health checks because the loop is frozen the whole time.\n"
        )

        # The threadpool is bounded -- that is the catch with the `def` answer.
        limiter = anyio.to_thread.current_default_thread_limiter()
        print(f"  AnyIO default thread limiter: {limiter.total_tokens} tokens.")
        print("  Enough concurrent blocking `def` endpoints and requests queue for a thread:")
        elapsed, _ = await _measure(
            client, "/sync-blocking", concurrent=int(limiter.total_tokens) + 20
        )
        print(
            f"  {int(limiter.total_tokens) + 20} concurrent /sync-blocking took {elapsed:.2f}s "
            f"(> {BLOCK}s: some waited for a free thread)\n"
        )


if __name__ == "__main__":
    asyncio.run(main())
