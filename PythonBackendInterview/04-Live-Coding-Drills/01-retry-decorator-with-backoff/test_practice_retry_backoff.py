"""Runs the SAME behaviour spec against your from-scratch stub.

Excluded from the default run (the stub raises NotImplementedError on purpose). Opt in with:

    uv run pytest 04-Live-Coding-Drills/01-retry-decorator-with-backoff -m practice
"""

from __future__ import annotations

from typing import Any

import pytest
import retry_backoff_cases as spec
from practice_retry_backoff import retry

pytestmark = pytest.mark.practice


@pytest.mark.parametrize("case", spec.SYNC_CASES, ids=lambda c: c.__name__[len("case_") :])
def test_sync(case: Any) -> None:
    case(retry)


@pytest.mark.parametrize("case", spec.ASYNC_CASES, ids=lambda c: c.__name__[len("case_") :])
async def test_async(case: Any) -> None:
    await case(retry)
