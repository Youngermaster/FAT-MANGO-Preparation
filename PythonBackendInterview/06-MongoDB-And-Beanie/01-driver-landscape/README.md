# The Async MongoDB Driver Landscape in 2026

> **Prompt as you will hear it:** *"What do you use to talk to MongoDB from an async Python
> service?"*

This looks like a warm-up. It is actually a **currency check** — the correct answer changed in
2026, and most tutorials, most blog posts, and most of the training data behind AI assistants
still give the old one. Getting it right is cheap signal; getting it wrong suggests you last
touched this stack three years ago.

---

## The short answer

> **`pymongo.AsyncMongoClient`.** Motor is deprecated.

---

## What changed

| | Then | Now |
|---|---|---|
| Async driver | `motor.motor_asyncio.AsyncIOMotorClient` | **`pymongo.AsyncMongoClient`** |
| Status | **Deprecated 2026-05-14**, critical fixes only until 2027-05-14 | The supported path |
| Beanie | built on Motor | **2.0 dropped Motor** for PyMongo Async |

**Why PyMongo Async is not just a rename:** Motor worked by delegating synchronous PyMongo calls to
a thread pool and wrapping the results in futures. PyMongo Async is *natively* asyncio — it does
the I/O on the event loop directly. That removes a thread hop per operation, which means lower
latency and higher throughput. Saying *why* it is faster is the part that lands.

Migration is mostly mechanical: `AsyncIOMotorClient` → `AsyncMongoClient`, and imports move from
`motor` to `pymongo`.

---

## Beanie 2.x breaking changes

Beanie 2.0 renamed everything that referenced Motor:

| Old | New |
|---|---|
| `Document.get_motor_collection()` | `get_pymongo_collection()` |
| `get_settings().motor_db` | `.pymongo_db` |
| `get_settings().motor_collection` | `.pymongo_collection` |
| `IndexModelField.from_motor_index_information()` | `from_pymongo_index_information()` |
| `multiprocessing_mode=` on `init_beanie` | removed |

**Version constraint worth knowing:** Beanie supports Python **3.10–3.13**, not 3.14 — while
FastAPI already supports 3.14. If someone asks "why is this project pinned to 3.13?", *that* is
the answer, and it is a nice concrete example for the "how do you handle dependency version
conflicts?" question.

This repo pins `requires-python = ">=3.13,<3.14"` for exactly that reason.

---

## Verify, don't remember

The versions this material was written against are asserted, not recalled:

```bash
uv run pytest 06-MongoDB-And-Beanie/01-driver-landscape
```

`test_driver_landscape.py` checks that `AsyncMongoClient` exists, that Motor is **not** installed,
and that Beanie is 2.x. If a future `uv sync` changes any of that, the test fails instead of this
page quietly becoming wrong.

---

## ODM or raw driver?

Another likely follow-up. Have an opinion:

| Use **Beanie** when | Use the **raw driver** when |
|---|---|
| Documents map cleanly to Pydantic models | You are writing heavy aggregation pipelines |
| You want validation at the boundary for free | Bulk ETL where per-document validation is the bottleneck |
| You want typed queries (`User.age > 18`) | You need a driver feature the ODM does not expose |
| Migrations and lifecycle hooks are useful | Performance work where you must control the exact query |

Beanie is Pydantic + PyMongo Async, so a `Document` **is** a `BaseModel` — the same class validates
HTTP input and persists. Convenient, and also the source of the most common design mistake: leaking
your database model as your API response model. Keep `XCreate` / `XRead` / `XInDB` separate.

Alternatives worth being able to name: **Odmantic** (similar, smaller), **MongoEngine** (sync,
older, not Pydantic-based), or just PyMongo Async with hand-written `dict` mapping.

---

## Say it out loud

> In 2026 the async driver is `pymongo.AsyncMongoClient` — Motor was deprecated in May 2026 and is
> in critical-fix-only mode. It is not just a rename: Motor delegated to a thread pool and wrapped
> the results, whereas PyMongo Async does the I/O natively on the event loop, so there is one less
> hop per operation. Beanie 2.0 followed and dropped Motor, which is why `get_motor_collection`
> became `get_pymongo_collection`. One practical consequence is that Beanie currently supports
> Python 3.10 through 3.13 while FastAPI already supports 3.14, so Beanie is what pins your
> interpreter version. I'd reach for Beanie when documents map cleanly onto Pydantic models and I
> want validation and typed queries for free, and drop to the raw driver for heavy aggregation
> pipelines or bulk work where per-document validation is the bottleneck.
