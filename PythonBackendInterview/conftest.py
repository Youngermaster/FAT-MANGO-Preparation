"""Root pytest configuration for the whole study folder.

Two jobs:

1. Make ``uv run pytest`` green on a fresh checkout with *no infrastructure running*. Tests
   marked ``@pytest.mark.mongo`` are skipped (not failed) when MongoDB is unreachable.
2. Give every exercise a shared MongoDB URL so the Mongo exercises do not each invent one.
"""

from __future__ import annotations

import os
import socket

import pytest

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
MONGO_HOST = "localhost"
MONGO_PORT = 27017


def _mongo_is_up(host: str = MONGO_HOST, port: int = MONGO_PORT, timeout: float = 0.25) -> bool:
    """Cheap TCP probe.

    Deliberately not a real ``AsyncMongoClient`` ping: this runs during collection, before any
    event loop exists, and a 250 ms connect attempt is enough to tell "docker compose is up"
    from "it isn't".
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip Mongo-dependent tests when there is nothing to connect to."""
    if _mongo_is_up():
        return

    skip_mongo = pytest.mark.skip(
        reason="MongoDB is not running. Start it with: docker compose up -d"
    )
    for item in items:
        if "mongo" in item.keywords:
            item.add_marker(skip_mongo)


@pytest.fixture(scope="session")
def mongo_url() -> str:
    """Connection string for the Compose-managed MongoDB."""
    return MONGO_URL
