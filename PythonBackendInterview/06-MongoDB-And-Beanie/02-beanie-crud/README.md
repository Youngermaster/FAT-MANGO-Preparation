# Beanie + MongoDB: Modelling, Indexes, Aggregation, Concurrency

> **Prompt as you will hear it:** *"Walk me through how you'd model this in MongoDB and what
> indexes you'd add."*

Everything on this page is **executed against a real MongoDB**, not described. The index claim is
verified with `explain()`, the concurrency claim by running ten concurrent claims, the transaction
claim on an actual replica set.

---

## Run it

```bash
docker compose up -d                                  # single-node replica set
uv run python 06-MongoDB-And-Beanie/02-beanie-crud/beanie_crud.py
uv run pytest 06-MongoDB-And-Beanie -m mongo          # 14 tests
```

Without the database running, the tests **skip** rather than fail (see the root `conftest.py`).

---

## 1. Embed or reference?

The first question of every MongoDB design discussion.

```python
class Customer(Document):
    address: Address | None  # EMBEDDED — a sub-model, stored inline


class Order(Document):
    customer: Link[Customer]  # REFERENCED — a separate document
```

**Embed** when the data is *owned* by the parent, has no independent lifecycle, and is always read
together with it. One document, one read, no join.

**Reference** when it is large, independently queried, updated on a different cadence, shared by
many parents, or **unbounded**.

That last word is the one to say: the **16 MB document limit** plus the *unbounded array
anti-pattern*. Embedding a customer's orders works beautifully until a customer has 50,000 of
them, at which point every read of that customer drags all of it across the wire. When growth has
no natural ceiling, reference — or use the **bucket pattern** (N items per document), which is how
you model time-series and logs.

**The slogan:** *data that is accessed together should be stored together.* Model for your query
patterns, not for normal forms.

---

## 2. Indexes and the ESR rule

```python
class Settings:
    indexes = [
        [("status", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
    ]
```

Compound index field order follows **ESR**:

> **E**quality first → **S**ort next → **R**ange last.

This index serves `find(status="paid").sort(created_at DESC)` with no blocking in-memory sort.
Proven, not asserted:

```python
explain["queryPlanner"]["winningPlan"]  →  IXSCAN, and no SORT stage
```

`test_compound_index_is_actually_used` asserts `IXSCAN in stages` **and** `SORT not in stages`.

Other index facts worth having ready:

- **Prefix rule.** An index on `{a, b, c}` serves queries on `{a}`, `{a,b}`, `{a,b,c}` — but not
  `{b}` or `{b,c}`. So one well-ordered compound index often replaces three single-field ones.
- **Covered query.** If a projection needs only indexed fields, Mongo answers from the index alone
  — `totalDocsExamined: 0`.
- **Reading `explain`.** `nReturned` ≈ `totalKeysExamined` is healthy. `totalDocsExamined` far
  above `nReturned` means the index is not selective. A `SORT` stage means a missing index.
- **Indexes are not free.** Every index is another structure to update on write, and more RAM in
  the working set. "Add an index" is a trade, not a fix.
- **Unique indexes are enforced by the database.** Application-level "check then insert" is two
  operations and races under concurrency; a unique index does not. Tested.

---

## 3. The Decimal128 trap (money)

This one is genuinely non-obvious and it bit while writing this file:

```python
total: Decimal  # writes fine, READS blow up
total: DecimalAnnotation  # correct
```

BSON has no `Decimal` type, so Beanie writes a `bson.Decimal128`. Coming back, Pydantic v2 rejects
it:

```
Decimal input should be an integer, float, string or Decimal object [input_type=Decimal128]
```

Writes succeed and reads fail — a bug that only appears once data exists.
`beanie.DecimalAnnotation` is `Annotated[Decimal, BeforeValidator(...)]` and converts on the way
in.

And never use `float` for money. `0.1 + 0.2 != 0.3`; float would *silently lose precision* rather
than fail, which is worse.

---

## 4. Aggregation

```python
Order.find(Order.status != "cancelled").aggregate(
    [
        {"$group": {"_id": "$status", "revenue": {"$sum": {"$toDecimal": "$total"}}}},
        {"$sort": {"revenue": -1}},
    ]
)
```

**`$match` first, always.** Only a leading `$match` can use an index; once a blocking stage has
run, later `$match` stages scan whatever the pipeline produced. Stage ordering is most of Mongo
performance work.

Other stages to be able to name: `$lookup` (left outer join), `$unwind` (expensive on big arrays),
`$facet` (results **and** total count in one round trip — the standard answer to "how do you return
a paginated list with a total?"), `$setWindowFields`, `$merge`/`$out`. Blocking stages have a
100 MB memory limit unless you pass `allowDiskUse`.

---

## 5. Cursor vs offset pagination

```python
Order.find(Order.id > after).sort(+Order.id).limit(page_size)  # keyset
Order.find_all().skip(offset).limit(page_size)  # offset
```

Two independent problems with `skip`:

1. **Cost grows with depth.** The server walks and discards `n` documents, so page 10,000 is slow
   in a way page 1 is not.
2. **Correctness.** Insertions shift the window, so a reader scrolling live sees **duplicates and
   gaps**. `test_cursor_pagination_is_stable_when_rows_are_inserted` inserts a row between pages
   and asserts no overlap.

Point 2 is the stronger argument and the one people forget. Offset is fine for a page-number UI
over stable data; keyset is right for infinite scroll and APIs.

---

## 6. Links and the Mongo N+1

```python
await Order.find_one(...)  # customer stays a lazy Link
await Order.find_one(..., fetch_links=True)  # issues a $lookup
```

`fetch_links=True` on a **list** endpoint is the Mongo flavour of N+1 — convenient on a detail
view, expensive across a page of results. Fixes: a `$lookup` aggregation you control, a batch
fetch of the referenced ids with `$in`, or denormalising the two or three fields you actually
display (`customer_name` on the order) and accepting the update cost.

---

## 7. Concurrency without transactions

```python
await Order.get_pymongo_collection().update_one(
    {"_id": order_id, "status": "pending"},  # the expected state is in the FILTER
    {"$set": {"status": "paid"}},
)
# modified_count == 1  ->  you won
```

Single-document updates are **atomic**, always. Putting the expected state in the filter turns
"claim this exactly once" into one round trip with no locks: ten concurrent claimers, one winner.
Tested with `asyncio.gather` over ten calls.

This is **optimistic locking**, and it is the answer to reach for *before* transactions. It is
cheaper, it works on a standalone server, and it covers most real cases. The generalised form adds
a `version` field to the filter and `$inc`s it.

**Multi-document transactions** exist since 4.0, need a **replica set** (hence `--replSet` in the
compose file), and are genuinely useful — but they hold resources, have a 60-second default limit,
and do not scale like single-document writes. The senior line: *design them away by embedding what
must change together; reach for one when the data genuinely spans documents.*

---

## 8. Why test against real MongoDB

A defensible opinion worth having:

- **`mongomock`** does not implement real index behaviour, the full aggregation language, or
  transactions — precisely the things worth testing.
- **`mongomock-motor`** is additionally stale for this stack: it mocks *Motor's* client, while
  Beanie 2.x runs on PyMongo Async.
- **Testcontainers / Compose** gives you the real engine. Slower, but the tests mean something.

Isolation here is **a fresh randomly-named database per test**, dropped in teardown — no
cross-test leakage, no ordering dependencies, and it works under `pytest-xdist`.

---

## Follow-ups they will ask next

**"Where does `init_beanie` go?"** In the FastAPI `lifespan`, once per process — never per
request. With N gunicorn workers it runs N times; index creation is idempotent so that is safe,
but for large collections build indexes in a **migration**, because building one at boot can stall
a rollout.

**"How do you do schema migrations?"** Beanie ships `beanie new-migration` with forward/backward
steps. The zero-downtime pattern is **expand/contract**: add the new field, backfill, dual-write,
switch reads, then drop the old field — each step independently deployable.

**"Write concern?"** `w: "majority"` for anything you cannot lose; `w: 1` is faster but a primary
failover can lose the write. Pair with read concern `"majority"` to avoid reading data that may
roll back.

**"When would you shard?"** When data or working set exceeds one server, or write throughput caps
out. Then the shard key is everything: high cardinality, high query frequency, and
**non-monotonic** — a timestamp or auto-increment key sends every write to one shard (the hot-shard
problem).

---

## Say it out loud

> I model for query patterns rather than normal forms — data accessed together is stored together.
> I embed when the child is owned by the parent, has no independent lifecycle, and is bounded;
> I reference when it is large, independently queried, or unbounded, because of the 16 MB document
> limit and the unbounded-array anti-pattern. For indexes I order compound keys by ESR — equality,
> then sort, then range — and I verify with `explain` that I get an IXSCAN and no blocking SORT
> stage. For pagination I prefer keyset over skip, not just because skip degrades with depth but
> because it produces duplicates and gaps when rows are inserted mid-scroll. For concurrency I
> reach for optimistic updates first: put the expected state in the filter, and single-document
> atomicity gives you exactly-once claiming in one round trip. Multi-document transactions work
> and need a replica set, but they are not free, so I prefer to design them away by embedding what
> has to change together. And for money I use Decimal, never float — with Beanie specifically that
> means `DecimalAnnotation`, because BSON stores Decimal128 and plain Pydantic `Decimal` fails on
> read.
