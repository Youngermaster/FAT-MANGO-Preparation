"""Beanie 2.x against a real MongoDB: documents, indexes, queries, aggregation, transactions.

Needs a running database:

    docker compose up -d
    uv run python 06-MongoDB-And-Beanie/02-beanie-crud/beanie_crud.py

Everything here uses `pymongo.AsyncMongoClient` -- Motor is deprecated and Beanie 2.0 dropped it.
See ../01-driver-landscape/.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

import pymongo
from beanie import DecimalAnnotation, Document, Indexed, Link, PydanticObjectId, init_beanie
from pydantic import BaseModel, Field
from pymongo import AsyncMongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")


# ==========================================================================================
# Documents
# ==========================================================================================


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class Address(BaseModel):
    """EMBEDDED, not referenced.

    An address is owned by its customer, has no independent lifecycle, and is always read
    together with them. That is the textbook case for embedding: one document, one read, no
    join. Compare with `Order.customer` below, which is a reference.
    """

    street: str
    city: str
    country: str


class Customer(Document):
    # `Indexed(...)` declares a single-field index inline. `unique=True` is enforced by the
    # DATABASE, which matters: application-level uniqueness checks race under concurrency
    # ("check then insert" is two operations), a unique index does not.
    email: Indexed(str, unique=True)  # type: ignore[valid-type]
    name: str
    address: Address | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "customers"


class Order(Document):
    # A Link is a DBRef-style reference. Resolving links is a `$lookup` under the hood, so a
    # list endpoint with `fetch_links=True` is the Mongo flavour of the N+1 problem.
    customer: Link[Customer]
    status: OrderStatus = OrderStatus.PENDING
    # MONEY: `DecimalAnnotation`, not `Decimal`, and never `float`.
    #
    # Float is wrong for money regardless of database -- 0.1 + 0.2 != 0.3, and rounding errors
    # in currency are an incident, not a curiosity.
    #
    # But plain `Decimal` is a trap here too, and this is a genuinely non-obvious one: BSON has
    # no `Decimal` type, so Beanie writes a `bson.Decimal128`. On the way back, Pydantic v2
    # rejects `Decimal128` with:
    #
    #     Decimal input should be an integer, float, string or Decimal object
    #     [input_type=Decimal128]
    #
    # so writes succeed and READS blow up -- a bug that only appears once data exists.
    # `beanie.DecimalAnnotation` is `Annotated[Decimal, BeforeValidator(...)]`, which converts
    # Decimal128 back on the way in. It behaves as a normal `Decimal` in Python.
    total: DecimalAnnotation
    item_count: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "orders"
        indexes = [
            # COMPOUND INDEX, ordered by the ESR rule:
            #   Equality first (status), then Sort (created_at), then Range.
            # This one index serves `find(status=X).sort(-created_at)` without a blocking
            # in-memory SORT stage.
            [("status", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
        ]


ALL_MODELS = [Customer, Order]


async def connect(database_name: str = "interview_demo") -> AsyncMongoClient:
    """Open the client and initialise Beanie.

    `init_beanie` registers the models AND creates the declared indexes, so it must run once at
    startup -- in FastAPI that means the `lifespan` handler, never per request.

    Note what happens with N gunicorn workers: lifespan runs once PER PROCESS, so all N try to
    create the same indexes. That is safe (index creation is idempotent) but it is a real
    interview question, and the answer for large collections is to create indexes in a
    migration instead of at boot, because building an index on a big collection at startup can
    stall the rollout.
    """
    client: AsyncMongoClient = AsyncMongoClient(MONGO_URL)
    await init_beanie(database=client[database_name], document_models=ALL_MODELS)
    return client


# ==========================================================================================
# Queries
# ==========================================================================================


async def create_customer(email: str, name: str, city: str = "Bogota") -> Customer:
    customer = Customer(
        email=email, name=name, address=Address(street="1 Main", city=city, country="CO")
    )
    await customer.insert()
    return customer


async def orders_by_status(status: OrderStatus, limit: int = 10) -> list[Order]:
    """Typed query: `Order.status == status` builds the Mongo filter from the model.

    This is the ODM's main ergonomic win over raw dicts -- a typo in a field name is caught by
    the type checker rather than silently matching zero documents, which is exactly how
    `{"stauts": "paid"}` returns an empty list and nobody notices.
    """
    return await Order.find(Order.status == status).sort(-Order.created_at).limit(limit).to_list()


class OrderSummary(BaseModel):
    """A projection model: fetch only these fields.

    Projections reduce network transfer and can enable a COVERED QUERY -- one answered entirely
    from the index without touching the documents at all.
    """

    id: PydanticObjectId = Field(alias="_id")
    status: OrderStatus
    total: DecimalAnnotation


async def order_summaries(limit: int = 10) -> list[OrderSummary]:
    return await Order.find_all().project(OrderSummary).limit(limit).to_list()


async def revenue_by_status() -> list[dict]:
    """Aggregation pipeline.

    `$match` goes FIRST so it can use an index -- once a blocking stage has run, later `$match`
    stages scan whatever the pipeline produced. Ordering the stages well is most of Mongo
    performance work.
    """
    return (
        await Order.find(Order.status != OrderStatus.CANCELLED)
        .aggregate(
            [
                {
                    "$group": {
                        "_id": "$status",
                        "revenue": {"$sum": {"$toDecimal": "$total"}},
                        "orders": {"$sum": 1},
                        "avg_items": {"$avg": "$item_count"},
                    }
                },
                {"$sort": {"revenue": -1}},
            ]
        )
        .to_list()
    )


async def paginate_by_cursor(after: PydanticObjectId | None, page_size: int = 2) -> list[Order]:
    """Keyset (cursor) pagination -- constant cost regardless of page depth.

    `skip(n)` makes the server walk and discard n documents, so page 10,000 is slow in a way
    page 1 is not. It also duplicates and drops rows when the data mutates mid-scroll. Using
    the last seen `_id` as a range boundary avoids both.
    """
    query = Order.find(Order.id > after) if after else Order.find_all()
    return await query.sort(+Order.id).limit(page_size).to_list()


# ==========================================================================================
# Concurrency: optimistic locking without a transaction
# ==========================================================================================


async def try_claim_order(order_id: PydanticObjectId) -> bool:
    """Atomically move an order pending -> paid, exactly once.

    The status is part of the FILTER, not just the update. Two concurrent callers both issue the
    same update; MongoDB applies single-document updates atomically, so the first matches and
    the second matches nothing. `modified_count == 1` tells the winner from the loser.

    This is the pattern to reach for before multi-document transactions: it is cheaper, it works
    on standalone servers, and it covers most "claim this item" cases.
    """
    result = await Order.get_pymongo_collection().update_one(
        {"_id": order_id, "status": OrderStatus.PENDING.value},
        {"$set": {"status": OrderStatus.PAID.value}},
    )
    return result.modified_count == 1


async def transfer_with_transaction(client: AsyncMongoClient, order_id: PydanticObjectId) -> None:
    """Multi-document transaction -- needs a replica set, which is why compose uses --replSet.

    The senior take: transactions in MongoDB are real but not free (they hold resources, have a
    60s default limit, and do not scale like single-document writes). Prefer to DESIGN them
    away by embedding things that must change together in one document. Reach for a transaction
    when the data genuinely spans documents.
    """
    async with client.start_session() as session, await session.start_transaction():
        await Order.get_pymongo_collection().update_one(
            {"_id": order_id}, {"$set": {"status": OrderStatus.SHIPPED.value}}, session=session
        )
        await Customer.get_pymongo_collection().update_one(
            {}, {"$inc": {"shipped_count": 1}}, session=session
        )


# ==========================================================================================
# Demo
# ==========================================================================================


async def main() -> None:
    client = await connect()
    db_name = "interview_demo"
    # Clean slate so the demo is repeatable.
    await client.drop_database(db_name)
    await init_beanie(database=client[db_name], document_models=ALL_MODELS)

    print("\n--- create ---")
    alice = await create_customer("alice@example.com", "Alice")
    print(f"  inserted customer {alice.id} ({alice.email})")

    # Unique index is enforced by the database, not by us.
    try:
        await create_customer("alice@example.com", "Impostor")
    except pymongo.errors.DuplicateKeyError:
        print("  duplicate email rejected by the unique index (not by application code)")

    orders = [
        Order(customer=alice, status=OrderStatus.PAID, total=Decimal("42.50"), item_count=3),
        Order(customer=alice, status=OrderStatus.PAID, total=Decimal("17.25"), item_count=1),
        Order(customer=alice, status=OrderStatus.PENDING, total=Decimal("99.99"), item_count=5),
        Order(customer=alice, status=OrderStatus.CANCELLED, total=Decimal("10.00")),
    ]
    await Order.insert_many(orders)
    print(f"  inserted {len(orders)} orders")

    print("\n--- typed query ---")
    paid = await orders_by_status(OrderStatus.PAID)
    print(f"  paid orders: {[str(o.total) for o in paid]}")

    print("\n--- projection ---")
    summaries = await order_summaries(limit=3)
    print(f"  {[(s.status.value, str(s.total)) for s in summaries]}")

    print("\n--- aggregation ---")
    for row in await revenue_by_status():
        print(f"  {row['_id']:<10} revenue={row['revenue']} orders={row['orders']}")

    print("\n--- cursor pagination ---")
    page1 = await paginate_by_cursor(None)
    page2 = await paginate_by_cursor(page1[-1].id)
    print(f"  page 1 ids: {[str(o.id)[-6:] for o in page1]}")
    print(f"  page 2 ids: {[str(o.id)[-6:] for o in page2]}  (no overlap, no skip)")

    print("\n--- explain: does the compound index get used? ---")
    explain = (
        await Order.get_pymongo_collection()
        .find({"status": "paid"}, sort=[("created_at", -1)])
        .explain()
    )
    stage = explain["queryPlanner"]["winningPlan"]
    print(f"  winning plan stage: {_stage_name(stage)}  (IXSCAN = index used, COLLSCAN = not)")
    stats = explain.get("executionStats", {})
    if stats:
        print(
            f"  docs examined: {stats.get('totalDocsExamined')} returned: {stats.get('nReturned')}"
        )

    print("\n--- optimistic locking: only one claimer wins ---")
    pending = await Order.find_one(Order.status == OrderStatus.PENDING)
    assert pending is not None
    results = await asyncio.gather(*(try_claim_order(pending.id) for _ in range(5)))
    print(f"  5 concurrent claims -> {sum(results)} winner, {results.count(False)} losers")

    print("\n--- multi-document transaction (needs a replica set) ---")
    try:
        await transfer_with_transaction(client, pending.id)
        print("  transaction committed")
    except pymongo.errors.OperationFailure as exc:
        first_line = str(exc).splitlines()[0]
        print(f"  transaction unavailable: {first_line[:80]}")

    await client.drop_database(db_name)
    await client.close()
    print()


def _stage_name(plan: dict) -> str:
    """Walk down the plan tree to the first real access stage."""
    while "inputStage" in plan:
        if plan.get("stage") in {"IXSCAN", "COLLSCAN"}:
            break
        plan = plan["inputStage"]
    return plan.get("stage", "?")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (pymongo.errors.ServerSelectionTimeoutError, pymongo.errors.ConnectionFailure):
        print(
            "\nMongoDB is not reachable. Start it first:\n"
            "    docker compose up -d\n"
            "(and make sure the Docker daemon itself is running)\n"
        )
