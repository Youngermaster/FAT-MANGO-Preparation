"""Proves each seeded bug is real and each fix actually fixes it.

Every test asserts the WRONG behaviour of the broken version and the RIGHT behaviour of the fixed
one. That matters: a "bug" that only exists in a comment is just an opinion.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from code_review_traps import (
    TRAPS,
    broken_add_tag,
    broken_count_errors,
    broken_drop_negatives,
    broken_fetch_all,
    broken_fetch_with_retry,
    broken_filter_allowed,
    broken_get_ids,
    broken_handler,
    broken_join,
    broken_make_handlers,
    broken_page_size,
    broken_parse_port,
    broken_read_config,
    broken_timed,
    broken_worker,
    fixed_add_tag,
    fixed_count_errors,
    fixed_drop_negatives,
    fixed_fetch_all,
    fixed_fetch_with_retry,
    fixed_filter_allowed,
    fixed_get_ids,
    fixed_handler,
    fixed_join,
    fixed_make_handlers,
    fixed_page_size,
    fixed_parse_port,
    fixed_read_config,
    fixed_timed,
    fixed_worker,
    validate_not_empty,
)


def test_every_trap_is_listed() -> None:
    assert len(TRAPS) == 15
    assert [n for n, _ in TRAPS] == list(range(1, 16))


# 1 -------------------------------------------------------------------------------------
def test_retry_returns_none_instead_of_raising() -> None:
    def always_fails() -> str:
        raise ConnectionError("down")

    assert broken_fetch_with_retry(always_fails) is None, "the bug: silent None"

    with pytest.raises(ConnectionError):
        fixed_fetch_with_retry(always_fails)


# 2 -------------------------------------------------------------------------------------
async def test_blocking_coroutine_freezes_the_loop() -> None:
    async def count_ticks(coro) -> int:  # noqa: ANN001
        ticks = 0
        stop = False

        async def ticker() -> None:
            nonlocal ticks
            while not stop:
                await asyncio.sleep(0.002)
                ticks += 1

        task = asyncio.create_task(ticker())
        await coro
        stop = True
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return ticks

    blocked = await count_ticks(broken_handler())
    healthy = await count_ticks(fixed_handler())

    assert blocked <= 1, f"the loop should be frozen, but it ticked {blocked} times"
    assert healthy > 5, f"the loop should stay responsive, only ticked {healthy}"


# 3 -------------------------------------------------------------------------------------
def test_mutable_default_is_shared() -> None:
    broken_add_tag.__defaults__[0].clear()
    assert broken_add_tag("a") == ["a"]
    assert broken_add_tag("b") == ["a", "b"], "second call sees the first call's data"

    assert fixed_add_tag("a") == ["a"]
    assert fixed_add_tag("b") == ["b"]


# 4 -------------------------------------------------------------------------------------
def test_late_binding_closures() -> None:
    assert [h() for h in broken_make_handlers()] == ["handler-2"] * 3
    assert [h() for h in fixed_make_handlers()] == ["handler-0", "handler-1", "handler-2"]


# 5 -------------------------------------------------------------------------------------
async def test_catching_baseexception_makes_a_task_uncancellable() -> None:
    log: list[str] = []
    task = asyncio.create_task(broken_worker(log))
    await asyncio.sleep(0.01)
    task.cancel()
    await asyncio.sleep(0.01)

    assert not task.cancelled(), "swallowing CancelledError defeated the cancellation"
    assert log == ["swallowed"]

    log2: list[str] = []
    task2 = asyncio.create_task(fixed_worker(log2))
    await asyncio.sleep(0.01)
    task2.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task2

    assert task2.cancelled(), "re-raising lets the cancellation through"
    assert log2 == ["cleaning up"], "cleanup still ran"


# 6 -------------------------------------------------------------------------------------
@pytest.mark.parametrize(("given", "expected"), [(0, 0), (10, 10), (None, 50)])
def test_or_default_swallows_zero(given: int | None, expected: int) -> None:
    assert fixed_page_size(given) == expected

    if given == 0:
        assert broken_page_size(given) == 50, "the bug: an explicit 0 becomes the default"


# 7 -------------------------------------------------------------------------------------
def test_streaming_matches_readlines(tmp_path) -> None:  # noqa: ANN001
    path = tmp_path / "app.log"
    path.write_text("INFO ok\nERROR bad\nERROR worse\nDEBUG x\n")

    assert broken_count_errors(str(path)) == 2
    assert fixed_count_errors(str(path)) == 2, "same answer, constant memory"


# 8 -------------------------------------------------------------------------------------
def test_join_is_equivalent_and_faster() -> None:
    items = [str(i) for i in range(2000)]
    assert broken_join(items) == fixed_join(items)

    started = time.perf_counter()
    broken_join(items)
    slow = time.perf_counter() - started

    started = time.perf_counter()
    fixed_join(items)
    fast = time.perf_counter() - started

    assert fast <= slow or fast < 0.01


# 9 -------------------------------------------------------------------------------------
def test_set_membership_matches_list_membership_and_is_faster() -> None:
    items = list(range(2000))
    allowed = list(range(1000, 3000))

    assert broken_filter_allowed(items, allowed) == fixed_filter_allowed(items, allowed)

    started = time.perf_counter()
    broken_filter_allowed(items, allowed)
    quadratic = time.perf_counter() - started

    started = time.perf_counter()
    fixed_filter_allowed(items, allowed)
    linear = time.perf_counter() - started

    assert linear < quadratic, f"set membership should win ({linear:.4f}s vs {quadratic:.4f}s)"


# 10 ------------------------------------------------------------------------------------
def test_mutating_while_iterating_skips_elements() -> None:
    """Two adjacent negatives: removing the first shifts the second into the slot the
    iterator has already passed, so it survives."""
    assert broken_drop_negatives([-1, -2, 3]) == [-2, 3], "the bug: -2 was skipped"
    assert fixed_drop_negatives([-1, -2, 3]) == [3]


# 11 ------------------------------------------------------------------------------------
def test_generator_is_single_use() -> None:
    rows = [{"id": 1}, {"id": 2}]

    gen = broken_get_ids(rows)
    assert list(gen) == [1, 2]
    assert list(gen) == [], "the bug: exhausted after one pass"
    with pytest.raises(TypeError):
        len(broken_get_ids(rows))  # type: ignore[arg-type]

    ids = fixed_get_ids(rows)
    assert list(ids) == [1, 2]
    assert list(ids) == [1, 2]
    assert len(ids) == 2


# 12 ------------------------------------------------------------------------------------
def test_bare_except_hides_a_config_error() -> None:
    assert broken_parse_port("80a") == 8080, "the bug: silently wrong port, nothing logged"

    with pytest.raises(ValueError, match="invalid port"):
        fixed_parse_port("80a")

    assert fixed_parse_port("9000") == 9000


# 13 ------------------------------------------------------------------------------------
async def test_bounded_fanout_limits_concurrency() -> None:
    peak = {"current": 0, "max": 0}

    async def fetch(url: str) -> str:
        peak["current"] += 1
        peak["max"] = max(peak["max"], peak["current"])
        await asyncio.sleep(0.01)
        peak["current"] -= 1
        return url

    urls = [f"u{i}" for i in range(50)]

    await broken_fetch_all(urls, fetch)
    assert peak["max"] == 50, "the bug: everything runs at once"

    peak["max"] = 0
    await fixed_fetch_all(urls, fetch, limit=5)
    assert peak["max"] == 5


# 14 ------------------------------------------------------------------------------------
def test_wraps_preserves_identity() -> None:
    assert broken_timed(validate_not_empty).__name__ == "wrapper", "the bug"
    assert broken_timed(validate_not_empty).__doc__ is None

    wrapped = fixed_timed(validate_not_empty)
    assert wrapped.__name__ == "validate_not_empty"
    assert wrapped.__doc__ == validate_not_empty.__doc__


# 15 ------------------------------------------------------------------------------------
def test_file_is_left_open_when_validation_raises(tmp_path) -> None:  # noqa: ANN001
    path = tmp_path / "config.txt"
    path.write_text("   ")  # whitespace only -> validate raises

    import gc
    import warnings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        with pytest.raises(ValueError):
            broken_read_config(str(path))
        gc.collect()

    assert any(issubclass(w.category, ResourceWarning) for w in caught), (
        "the bug: the descriptor leaked, which Python reports as a ResourceWarning"
    )

    # The fixed version closes on the error path, so no warning.
    with warnings.catch_warnings(record=True) as caught2:
        warnings.simplefilter("always", ResourceWarning)
        with pytest.raises(ValueError):
            fixed_read_config(str(path))
        gc.collect()

    assert not any(issubclass(w.category, ResourceWarning) for w in caught2)

    path.write_text("host=localhost")
    assert fixed_read_config(str(path)) == "host=localhost"
