"""Beanie against a real MongoDB.

Marked `mongo`, so these auto-skip when the database is not running (see the root conftest.py).
To run them:

    docker compose up -d
    uv run pytest 06-MongoDB-And-Beanie -m mongo

Testing against real MongoDB rather than a mock is a deliberate choice worth defending in an
interview: mongomock does not implement real index behaviour, the full aggregation language, or
transactions -- which are exactly the things worth testing. `mongomock-motor` is additionally
stale here, since it mocks Motor's client while Beanie 2.x runs on PyMongo Async.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from decimal import Decimal

import pymongo
import pytest
from beanie import init_beanie
from beanie_crud import (
    ALL_MODELS,
    Address,
    Customer,
    Order,
    OrderStatus,
    OrderSummary,
    order_summaries,
    orders_by_status,
    paginate_by_cursor,
    revenue_by_status,
    try_claim_order,
)
from pymongo import AsyncMongoClient

pytestmark = pytest.mark.mongo


@pytest.fixture
async def db(mongo_url: str) -> AsyncIterator[AsyncMongoClient]:
    """A dedicated, randomly-named database per test.

    Isolation strategy matters and is a likely follow-up. A fresh database per test is the
    simplest correct option: no cross-test leakage, no ordering dependencies, and it works
    under `pytest-xdist`. The cost is index re-creation per test, which is negligible here.
    """
    name = f"test_{uuid.uuid4().hex[:12]}"
    client: AsyncMongoClient = AsyncMongoClient(mongo_url)
    await init_beanie(database=client[name], document_models=ALL_MODELS)
    try:
        yield client
    finally:
        await client.drop_database(name)
        await client.close()


@pytest.fixture
async def customer(db: AsyncMongoClient) -> Customer:
    c = Customer(
        email="alice@example.com",
        name="Alice",
        address=Address(street="1 Main", city="Bogota", country="CO"),
    )
    await c.insert()
    return c


# ------------------------------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------------------------------


async def test_insert_and_get(db: AsyncMongoClient, customer: Customer) -> None:
    found = await Customer.get(customer.id)
    assert found is not None
    assert found.email == "alice@example.com"
    assert found.address is not None
    assert found.address.city == "Bogota", "embedded documents round-trip as nested models"


async def test_unique_index_is_enforced_by_the_database(
    db: AsyncMongoClient, customer: Customer
) -> None:
    """Not by application code -- a check-then-insert in Python races under concurrency."""
    with pytest.raises(pymongo.errors.DuplicateKeyError):
        await Customer(email="alice@example.com", name="Impostor").insert()


async def test_update_and_delete(db: AsyncMongoClient, customer: Customer) -> None:
    customer.name = "Alice B"
    await customer.save()
    assert (await Customer.get(customer.id)).name == "Alice B"  # type: ignore[union-attr]

    await customer.delete()
    assert await Customer.get(customer.id) is None


async def test_decimal_round_trips_without_precision_loss(
    db: AsyncMongoClient, customer: Customer
) -> None:
    """The Decimal128 trap: writes succeed with plain `Decimal`, reads blow up.

    `beanie.DecimalAnnotation` converts BSON Decimal128 back on the way in. Using `float` here
    would silently lose precision instead of failing -- much worse.
    """
    await Order(customer=customer, total=Decimal("19.99")).insert()
    fetched = await Order.find_one(Order.total == Decimal("19.99"))
    assert fetched is not None
    assert fetched.total == Decimal("19.99")
    assert str(fetched.total) == "19.99"


# ------------------------------------------------------------------------------------------
# Queries
# ------------------------------------------------------------------------------------------


@pytest.fixture
async def orders(db: AsyncMongoClient, customer: Customer) -> list[Order]:
    """Insert a fixed set of orders and return them AS PERSISTED.

    Note the re-fetch. `insert_many` is a bulk write: it does not populate `id` back onto the
    Python objects you passed in, so `batch[0].id` is still `None` afterwards. That is a real
    difference from `.insert()` on a single document, and it is the kind of detail that turns
    into a confusing `NoneType` error three layers away. Re-reading is the honest fix.
    """
    batch = [
        Order(customer=customer, status=OrderStatus.PAID, total=Decimal("42.50"), item_count=3),
        Order(customer=customer, status=OrderStatus.PAID, total=Decimal("17.25"), item_count=1),
        Order(customer=customer, status=OrderStatus.PENDING, total=Decimal("99.99"), item_count=5),
        Order(customer=customer, status=OrderStatus.CANCELLED, total=Decimal("10.00")),
    ]
    await Order.insert_many(batch)
    assert batch[0].id is None, "insert_many does not backfill ids onto the input objects"
    return await Order.find_all().sort(+Order.id).to_list()


async def test_typed_query_filters_by_status(db: AsyncMongoClient, orders: list[Order]) -> None:
    paid = await orders_by_status(OrderStatus.PAID)
    assert len(paid) == 2
    assert {str(o.total) for o in paid} == {"42.50", "17.25"}


async def test_projection_returns_only_selected_fields(
    db: AsyncMongoClient, orders: list[Order]
) -> None:
    summaries = await order_summaries()
    assert len(summaries) == 4
    assert all(isinstance(s, OrderSummary) for s in summaries)
    assert not hasattr(summaries[0], "item_count"), "projected model has no such field"


async def test_aggregation_groups_and_sums(db: AsyncMongoClient, orders: list[Order]) -> None:
    rows = {row["_id"]: row for row in await revenue_by_status()}

    assert "cancelled" not in rows, "$match excluded cancelled before grouping"
    assert rows["paid"]["orders"] == 2
    assert Decimal(str(rows["paid"]["revenue"])) == Decimal("59.75")
    assert rows["paid"]["avg_items"] == 2.0


async def test_compound_index_is_actually_used(db: AsyncMongoClient, orders: list[Order]) -> None:
    """The point of the ESR ordering: equality, then sort -- no blocking in-memory SORT stage.

    `IXSCAN` means the index answered it. `COLLSCAN` would mean a full collection scan, which is
    what you get when the index does not match the query shape.
    """
    explain = (
        await Order.get_pymongo_collection()
        .find({"status": "paid"}, sort=[("created_at", -1)])
        .explain()
    )

    plan = explain["queryPlanner"]["winningPlan"]
    stages = []
    while plan:
        stages.append(plan.get("stage"))
        plan = plan.get("inputStage")

    assert "IXSCAN" in stages, f"expected the compound index to be used, got {stages}"
    assert "SORT" not in stages, "the index provides the ordering, so no blocking sort is needed"


async def test_cursor_pagination_has_no_overlap(db: AsyncMongoClient, orders: list[Order]) -> None:
    page1 = await paginate_by_cursor(None, page_size=2)
    page2 = await paginate_by_cursor(page1[-1].id, page_size=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert {o.id for o in page1}.isdisjoint({o.id for o in page2})


async def test_cursor_pagination_is_stable_when_rows_are_inserted(
    db: AsyncMongoClient, customer: Customer, orders: list[Order]
) -> None:
    """The real argument for keyset over offset pagination.

    With `skip`, inserting a row before the cursor shifts everything and the reader sees a
    duplicate. A keyset boundary is anchored to a value, so it is immune.
    """
    page1 = await paginate_by_cursor(None, page_size=2)
    await Order(customer=customer, total=Decimal("1.00")).insert()
    page2 = await paginate_by_cursor(page1[-1].id, page_size=2)

    assert {o.id for o in page1}.isdisjoint({o.id for o in page2})


# ------------------------------------------------------------------------------------------
# Links / N+1
# ------------------------------------------------------------------------------------------


async def test_links_are_not_resolved_unless_requested(
    db: AsyncMongoClient, orders: list[Order]
) -> None:
    """Default is a lazy `Link`; `fetch_links=True` issues a $lookup.

    That is the Mongo N+1: convenient on a detail endpoint, expensive on a list endpoint.
    """
    from beanie import Link

    lazy = await Order.find_one(Order.status == OrderStatus.PAID)
    assert lazy is not None
    assert isinstance(lazy.customer, Link), "not fetched by default"

    eager = await Order.find_one(Order.status == OrderStatus.PAID, fetch_links=True)
    assert eager is not None
    assert isinstance(eager.customer, Customer)
    assert eager.customer.email == "alice@example.com"


# ------------------------------------------------------------------------------------------
# Concurrency
# ------------------------------------------------------------------------------------------


async def test_optimistic_claim_has_exactly_one_winner(
    db: AsyncMongoClient, orders: list[Order]
) -> None:
    """Put the expected state in the FILTER, and single-document atomicity does the rest."""
    import asyncio

    pending = await Order.find_one(Order.status == OrderStatus.PENDING)
    assert pending is not None

    results = await asyncio.gather(*(try_claim_order(pending.id) for _ in range(10)))

    assert sum(results) == 1, f"exactly one claim must win, got {sum(results)}"
    assert (await Order.get(pending.id)).status == OrderStatus.PAID  # type: ignore[union-attr]


async def test_transaction_commits_on_a_replica_set(
    db: AsyncMongoClient, orders: list[Order]
) -> None:
    """Requires `--replSet`, which is why docker-compose.yml runs a single-node replica set.

    On a standalone server this raises OperationFailure -- multi-document transactions are a
    replica-set feature.
    """
    target = orders[0]
    async with db.start_session() as session, await session.start_transaction():
        await Order.get_pymongo_collection().update_one(
            {"_id": target.id}, {"$set": {"status": "shipped"}}, session=session
        )

    assert (await Order.get(target.id)).status == OrderStatus.SHIPPED  # type: ignore[union-attr]


async def test_transaction_rolls_back_on_error(db: AsyncMongoClient, orders: list[Order]) -> None:
    target = orders[0]
    original = target.status

    with pytest.raises(RuntimeError):
        async with db.start_session() as session, await session.start_transaction():
            await Order.get_pymongo_collection().update_one(
                {"_id": target.id}, {"$set": {"status": "shipped"}}, session=session
            )
            raise RuntimeError("something went wrong after the write")

    assert (await Order.get(target.id)).status == original  # type: ignore[union-attr]
