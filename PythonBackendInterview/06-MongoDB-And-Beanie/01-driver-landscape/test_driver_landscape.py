"""Asserts the version claims in this section's README instead of trusting them.

If a future `uv sync` pulls a different set of packages, these fail loudly rather than letting the
material quietly become one of the stale tutorials it warns about.

No MongoDB server needed -- this is pure introspection.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import sys

import pytest


def test_pymongo_exposes_the_native_async_client() -> None:
    """The 2026 answer: `pymongo.AsyncMongoClient`, not `motor.motor_asyncio`."""
    from pymongo import AsyncMongoClient

    assert AsyncMongoClient is not None


def test_motor_is_not_installed() -> None:
    """Motor was deprecated 2026-05-14. This project deliberately does not depend on it."""
    assert importlib.util.find_spec("motor") is None, (
        "motor should not be installed -- pymongo.AsyncMongoClient replaces it"
    )


def test_beanie_is_v2_or_newer() -> None:
    """Beanie 2.0 is the release that dropped Motor for PyMongo Async."""
    import beanie

    major = int(beanie.__version__.split(".")[0])
    assert major >= 2, f"expected Beanie 2.x, got {beanie.__version__}"


def test_beanie_uses_the_pymongo_naming() -> None:
    """The 2.0 rename: `get_motor_collection` -> `get_pymongo_collection`."""
    from beanie import Document

    assert hasattr(Document, "get_pymongo_collection"), "Beanie 2.x renamed this accessor"
    assert not hasattr(Document, "get_motor_collection"), "the Motor-era name should be gone"


def test_interpreter_is_within_beanies_supported_range() -> None:
    """Beanie supports 3.10-3.13, which is why this project pins <3.14 even though FastAPI
    already supports 3.14. A concrete answer to 'how do you handle version conflicts?'."""
    assert (3, 10) <= sys.version_info[:2] <= (3, 13), (
        f"Python {sys.version_info.major}.{sys.version_info.minor} is outside Beanie's range"
    )


@pytest.mark.parametrize(
    ("package", "minimum"),
    [("fastapi", (0, 141)), ("pydantic", (2, 13)), ("pymongo", (4, 15)), ("beanie", (2, 2))],
)
def test_pinned_versions_are_at_least_what_the_docs_assume(
    package: str, minimum: tuple[int, ...]
) -> None:
    raw = importlib.metadata.version(package)
    parsed = tuple(int(part) for part in raw.split(".")[: len(minimum)])
    assert parsed >= minimum, f"{package} {raw} is older than the documented {minimum}"


def test_pydantic_v2_api_shape() -> None:
    """A quick v1-vs-v2 litmus: the methods renamed, and BaseSettings moved out of pydantic."""
    from pydantic import BaseModel

    class M(BaseModel):
        x: int

    m = M(x=1)
    assert hasattr(m, "model_dump"), "v2 renamed .dict() -> .model_dump()"
    assert hasattr(M, "model_validate"), "v2 renamed .parse_obj() -> .model_validate()"

    # The v1 names still EXIST in v2 as deprecated shims -- they warn rather than disappear.
    # Worth knowing precisely: "it was removed" is wrong, "it warns and will be removed" is right.
    with pytest.warns(DeprecationWarning):
        M.parse_obj({"x": 1})
    with pytest.warns(DeprecationWarning):
        m.dict()

    # `BaseSettings` moved to the separate `pydantic-settings` package in v2. Pydantic keeps a
    # migration shim that RAISES a pointed error rather than simply being absent -- so the
    # accurate statement is "it moved and pydantic tells you where", not "it was deleted".
    import pydantic

    with pytest.raises(pydantic.errors.PydanticImportError, match="pydantic-settings"):
        _ = pydantic.BaseSettings  # type: ignore[attr-defined]

    from pydantic_settings import BaseSettings

    assert BaseSettings is not None
