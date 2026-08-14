# The Playbook

How to use this repo, how the hour is likely to go, and what to do in it.

---

## The format to expect

Reports from senior Python interviews at consultancy/outsourcing firms are remarkably consistent:

1. **A broad theory sweep.** Not quiz-fire — a discussion that keeps asking *"and how does that
   work underneath?"* until you reach the edge of your knowledge. They are calibrating your level,
   not catching you out.
2. **One practical live-coding task**, 20–40 minutes. Utility-flavoured, not LeetCode Hard: a
   decorator, a cache, a parser, a bounded fan-out. Candidates report doing it in a **plain
   editor** — no autocomplete, no linter, no test runner.
3. **Architecture and operations**, for senior roles specifically: microservices, deployment
   strategies (blue-green / canary / rolling), observability, testing practice.
4. **Communication throughout.** In a 100%-English environment with a non-native-English
   interviewer, clarity beats vocabulary. Short sentences win.

The single most important consequence: **practice without assistance.** Turn off Copilot and any
AI autocomplete *now*, so the muscle is trained by Monday. That is what the `practice_*.py` stubs
in this repo are for.

---

## Reaching the edge of what you know

You *will* be asked something you do not know — that is the design of the format, not a failure.
The response that scores well:

> "I haven't used that directly. What I'd expect is X, because Y. Is that right?"

Then actually listen to the answer. This reads as senior. Bluffing does not, and an interviewer
with eight years in the language will spot it inside one follow-up.

Equally: **volunteer the objections to your own code.** In the retry decorator, saying "and this
needs jitter, otherwise a fleet of workers retries in lockstep" *before* they ask is worth more
than the code itself.

---

## Live coding: the sequence

1. **Restate the problem.** "So: retry a function N times, backing off between attempts. Should it
   work for async functions too?" — thirty seconds that prevents solving the wrong problem.
2. **Ask about the edges before writing.** Which exceptions retry? Is there a cap? What happens
   when it finally fails? Every one of those is a point scored.
3. **Say your plan in one sentence**, then write.
4. **Narrate while typing** — sparsely, not a monologue. "I'll re-raise here so the caller doesn't
   get a silent `None`."
5. **Test it out loud.** Walk one happy path and one edge case by hand.
6. **Volunteer the improvements** you would make with more time.

If you go blank: say what you *do* know, write the simplest thing that could work, then improve it.
A working naive solution you then critique beats a perfect solution you never reach.

---

## Ordering the weekend

Roughly 16–20 hours across Friday evening, Saturday and Sunday. Weight it by *probability × your
gap*, not by what is most fun to read.

### Friday evening (~2h) — orientation
- Run `./check.sh` so everything is installed and green.
- `02-Async-And-Concurrency/05-blocking-the-loop` — run it, watch the health checks die.
- `04-Live-Coding-Drills/01-retry-decorator-with-backoff` — read the README, then do the practice
  stub cold.

### Saturday (~8h) — Python depth + async
| Block | Topic |
|---|---|
| 2.5h | `02-Async-And-Concurrency/` — event loop, blocking, gather vs TaskGroup, cancellation, semaphores |
| 2h | `04-Live-Coding-Drills/` — retry, LRU, flatten. **Practice stubs, not the solutions.** |
| 2h | `01-Python-Core/` — gotchas, decorators, generators, context managers |
| 1.5h | `01-Python-Core/` — GIL, threads vs processes, memory model |

### Sunday (~8h) — stack + rehearsal
| Block | Topic |
|---|---|
| 2h | `05-FastAPI/` — sync vs async endpoints, DI, lifespan, testing |
| 1.5h | `06-MongoDB-And-Beanie/` — `docker compose up -d` and run it for real |
| 1.5h | `07-Auth-Security/` — OAuth2 vs OIDC, JWT validation, PKCE |
| 1h | `08-System-Design/` — pick two prompts, answer them out loud |
| 2h | **Full rehearsal in English.** Introduce yourself, answer five questions aloud, solve one drill timed. Record it and listen back. |

### Monday morning — nothing new
Re-read `rapid-fire-qa.md` and your "say it out loud" paragraphs. Check camera, mic, headphones and
screen share. Close every AI tool and note-taker. Water. One monitor. Join five minutes early.

---

## If you only have three hours

1. `02-Async-And-Concurrency/05-blocking-the-loop` — run it, read it, learn the FastAPI
   `def` vs `async def` table cold.
2. `04-Live-Coding-Drills/01-retry-decorator-with-backoff` — write it from the blank stub until
   fluent, sync and async.
3. Every **"Say it out loud"** section in this repo, read aloud. They are written to be spoken, not
   skimmed.

---

## The five answers most worth having ready

1. **Blocking the event loop** — and the counter-intuitive fact that a plain `def` endpoint is
   *safer* for blocking work than `async def`. → `02-Async-And-Concurrency/05-blocking-the-loop`
2. **GIL, correctly stated** — never "Python can't do threads". It limits *parallelism* for
   CPU-bound work; I/O releases it. asyncio for I/O concurrency, processes for CPU.
3. **Retry with backoff and jitter** — including *why* jitter, and which exceptions deserve a retry.
4. **Mongo modelling** — embed vs reference, the 16 MB limit, ESR index ordering, and why keyset
   beats offset pagination.
5. **Your own language narrative** — backend experience is continuous; the language alternated with
   the project. Async, DI, API design, schema validation, microservices transferred directly. Have
   your strongest recent Python project ready in one sentence, because *"what's the most complex
   Python thing you've built?"* is certain.

---

## Files here

| File | What it is |
|---|---|
| `rapid-fire-qa.md` | ~100 questions with short spoken answers. Cover the answer column and drill. |
| `code_review_traps.py` | Fifteen snippets with seeded bugs — *"what's wrong with this?"* |
| `test_code_review_traps.py` | Proves each bug is real, and that each fix works |

---

## Two honest framings worth rehearsing

**On AI tooling.** The role explicitly wants AI-assisted development experience, and the interview
explicitly forbids it. Both are consistent: they want engineers who can *review and validate* what
a model produces, which requires being able to write it yourself. If asked, that is the answer —
you use these tools daily for velocity, and you keep the judgment to reject their output.

**On not knowing.** "I don't know, here's how I'd find out" is a complete, respectable answer.
Use it early so it costs nothing later.
