"""Runs the shared behaviour spec against the reference solution."""

from __future__ import annotations

from typing import Any

import pytest
import retry_backoff_cases as spec
from retry_backoff import retry


@pytest.mark.parametrize("case", spec.SYNC_CASES, ids=lambda c: c.__name__[len("case_") :])
def test_sync(case: Any) -> None:
    case(retry)


@pytest.mark.parametrize("case", spec.ASYNC_CASES, ids=lambda c: c.__name__[len("case_") :])
async def test_async(case: Any) -> None:
    await case(retry)
