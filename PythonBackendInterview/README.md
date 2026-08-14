# Senior Python Backend — Interview Preparation

Runnable, explained, and **verified** preparation for a senior Python backend interview.
Target stack: **Python 3.13 · FastAPI · async/await · MongoDB + Beanie · OAuth2/OIDC/JWT ·
Docker · pytest**.

Every claim on every page is executed. The event-loop demo *measures* the damage, the index page
reads a real `explain()` plan, the version notes are asserted by tests. Nothing here is recalled
from a blog post.

---

## Start here

```bash
cd PythonBackendInterview
uv sync            # provisions Python 3.13 + all dependencies
./check.sh         # lint + format + tests + smoke-run every exercise
```

`./check.sh` should end with **`all checks passed`**. Then:

```bash
docker compose up -d                 # MongoDB, as a single-node replica set
uv run pytest -m mongo               # the database-backed exercises
```

Without Docker running, Mongo tests **skip** rather than fail — the suite is green on a bare
checkout.

Read [`00-Interview-Playbook/README.md`](00-Interview-Playbook/README.md) first. It has the format
to expect, how to behave in a live-coding round, and the weekend schedule.

---

## How each exercise is laid out

```
NN-topic-name/
├── README.md              Problem · why it's asked · walkthrough · follow-ups · "say it out loud"
├── <topic>.py             The solution, commented as if narrating it
├── <topic>_naive.py       (sometimes) the version that fails review, with the objections
├── practice_<topic>.py    (drills) a blank stub — start here
└── test_<topic>.py        The behaviour spec
```

Every `README.md` ends with a **“Say it out loud”** paragraph — the answer written to be *spoken*,
at the length you would actually say it. Read those aloud. They are the highest-value part of the
repo and they do not work if you skim them.

### Practice mode — the important bit

The interview forbids AI assistance, and candidates report writing code in a plain editor with no
autocomplete. So the drills ship with **blank stubs** and the *same* test suite:

```bash
uv run pytest 04-Live-Coding-Drills/01-retry-decorator-with-backoff -m practice
```

Excluded from the default run (the stubs raise `NotImplementedError` on purpose). Write the
implementation from scratch, run the spec, repeat until fluent. **Turn Copilot off now** so the
muscle is trained by Monday.

---

## Sections

| | Section | What is in it |
|---|---|---|
| 00 | [**Interview Playbook**](00-Interview-Playbook/) | Format, weekend schedule, ~100-question [rapid-fire Q&A](00-Interview-Playbook/rapid-fire-qa.md), and 15 [code-review traps](00-Interview-Playbook/code_review_traps.py) with seeded bugs |
| 01 | [**Python Core**](01-Python-Core/) | [Mutability, closures, identity, copying](01-Python-Core/02-mutability-and-gotchas/) — the "what does this print?" round |
| 02 | [**Async & Concurrency**](02-Async-And-Concurrency/) | [gather vs TaskGroup vs as_completed](02-Async-And-Concurrency/03-gather-taskgroup-as-completed/) · [blocking the loop](02-Async-And-Concurrency/05-blocking-the-loop/) · [bounded fan-out](02-Async-And-Concurrency/06-semaphores-and-concurrency-limits/) |
| 03 | [**Algorithms & Data Structures**](03-Algorithms-And-Data-Structures/) | patterns mapped to backend use cases · [measured Big-O of Python builtins](03-Algorithms-And-Data-Structures/00-complexity-cheatsheet/) |
| 04 | [**Live-Coding Drills**](04-Live-Coding-Drills/) | [retry + backoff](04-Live-Coding-Drills/01-retry-decorator-with-backoff/) · [LRU cache](04-Live-Coding-Drills/02-lru-cache-from-scratch/) · [flatten nested dict](04-Live-Coding-Drills/03-flatten-nested-dict/) |
| 05 | [**FastAPI**](05-FastAPI/) | [sync vs async endpoints](05-FastAPI/01-sync-vs-async-endpoints/) · [dependency injection](05-FastAPI/02-dependency-injection/) |
| 06 | [**MongoDB & Beanie**](06-MongoDB-And-Beanie/) | [driver landscape](06-MongoDB-And-Beanie/01-driver-landscape/) · [modelling, indexes, aggregation, concurrency](06-MongoDB-And-Beanie/02-beanie-crud/) |
| 07 | [**Auth & Security**](07-Auth-Security/) | [JWT validation, OAuth 2.1, OIDC](07-Auth-Security/01-jwt-validation/) — with working forgery attacks |

**Coverage note.** The sections above are complete and tested. The numbering leaves room for
topics not yet written — more Python-core exercises (decorators, generators, context managers,
typing, GIL), more drills, more FastAPI topics (lifespan, Pydantic v2, streaming, testing), plus
System Design, Testing/DevOps and an FHIR primer. What is here is the highest-probability material,
built first on purpose.

---

## The three demos worth running first

They produce numbers, and the numbers are the lesson.

**1. Blocking the event loop** — a heartbeat ticks every 10 ms while 0.3 s of work happens:

```
async def + time.sleep()   <- THE BUG           0.30s  ticks   0/30  LOOP BLOCKED
asyncio.to_thread(blocking_io)                  0.31s  ticks  27/30  OK
```

**2. `def` vs `async def` endpoints** — the counter-intuitive one:

```
/async-blocking        1.02s   1 health check served   <- serialised AND froze the server
/sync-blocking         0.29s  42 health checks served  <- threadpool, loop stayed free
```

**3. Bounded fan-out** — the limit actually holding:

```
unbounded gather     -> peak concurrency 200
semaphore(limit=5)   -> peak concurrency 5
```

---

## Version reality, 2026

Most tutorials — and most AI training data — are wrong about these. Each is asserted by
`06-MongoDB-And-Beanie/01-driver-landscape/test_driver_landscape.py`, so an upgrade breaks the test
instead of quietly making the docs wrong.

| Thing | The current answer |
|---|---|
| Async Mongo driver | **`pymongo.AsyncMongoClient`** — Motor deprecated 2026-05-14 |
| Beanie | **2.x dropped Motor**; `get_motor_collection()` → `get_pymongo_collection()` |
| Python version | Beanie supports **3.10–3.13**, not 3.14 — that is what pins this project |
| Money in Beanie | **`DecimalAnnotation`** — plain `Decimal` writes fine and **fails on read** |
| httpx | `AsyncClient(app=app)` **removed in 0.28** — use `ASGITransport(app=app)` |
| pytest-asyncio | the `event_loop` fixture was **removed in 1.0** |
| FastAPI startup | `@app.on_event` deprecated → `lifespan` |
| Pydantic v2 | `BaseSettings` moved to `pydantic-settings`; `Optional[X]` no longer implies a default |
| OAuth | **2.1 removed implicit and password grants**; PKCE mandatory for public clients |
| Tooling | `ruff` replaces black+isort+flake8; `uv` replaces pip/poetry for most work |

Verified on: Python 3.13.13 · FastAPI 0.141.1 · Starlette 1.6.0 · Pydantic 2.13.4 ·
Beanie 2.2.0 · PyMongo 4.17.0 · pytest 9.1.1 · pytest-asyncio 1.4.0.

---

## Commands

```bash
./check.sh                              # everything
uv run pytest                           # all tests (practice stubs excluded)
uv run pytest -m practice               # your from-scratch attempts
uv run pytest -m mongo                  # database-backed (needs docker compose up -d)
uv run pytest 05-FastAPI -v             # one section
uv run python <path-to-any-solution>.py # every solution runs standalone
uv run ruff check . && uv run ruff format .
docker compose up -d && docker compose down -v
```

---

## Why the module names are not `solution.py`

Test files import their neighbour directly (`from retry_backoff import retry`), which relies on
pytest putting each test's own directory on `sys.path`. That makes **module basenames global**: two
files both called `solution.py` would collide in `sys.modules` and the second would silently
resolve to the first. So each exercise module is named after its topic.

That is not incidental trivia — "how does Python resolve imports, and when do two modules collide?"
is a fair interview question, and this repo's layout is the answer.
