# LRU Cache from Scratch

> **Prompt as you will hear it:** *"Implement an LRU cache with O(1) get and put."*

---

## Why this one comes up so often

It is the most-asked design-a-data-structure question for backend engineers, because caching is
the most common thing a backend engineer actually does. It checks whether you can compose *two*
data structures to hit a complexity target that neither reaches alone:

- A dict gives O(1) lookup but has no notion of recency.
- A list gives you ordering but O(n) removal from the middle.
- A dict **of nodes in a doubly linked list** gives you both.

The interviewer is watching for whether you reach for `OrderedDict` (stdlib fluency) *and* can
explain what it is doing underneath (data-structure understanding). Do both, in that order.

---

## Files

| File | What it is |
|---|---|
| `lru_cache_impl.py` | Both implementations: `LRUCacheOrderedDict` and `LRUCache` |
| `lru_cache_cases.py` | The behaviour spec — 14 cases, including a randomised model-check |
| `practice_lru_cache.py` | Blank stub. **Start here.** |
| `test_lru_cache.py` | Spec run against both solutions and your stub |

```bash
uv run pytest 04-Live-Coding-Drills/02-lru-cache-from-scratch              # 28 pass
uv run pytest 04-Live-Coding-Drills/02-lru-cache-from-scratch -m practice  # your attempt
uv run python 04-Live-Coding-Drills/02-lru-cache-from-scratch/lru_cache_impl.py
```

---

## Walkthrough

### Start with the 10-line answer

```python
class LRUCache:
    def __init__(self, capacity):
        self.capacity, self._data = capacity, OrderedDict()

    def get(self, key, default=None):
        if key not in self._data:
            return default
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)
```

`OrderedDict` *is* a dict plus a doubly linked list of its keys — the exact structure this problem
needs, already implemented in C. `move_to_end` is O(1); `popitem(last=False)` pops the front, the
least-recently-used, in O(1).

**Volunteer the follow-up before they ask it:** a plain `dict` also preserves insertion order
(guaranteed since 3.7), but it has no `move_to_end` and no O(1) pop-from-front, so it cannot
express "touch" or "evict oldest" cheaply. That is why `OrderedDict` still exists.

Then say: *"That is the version I would ship. Let me write what it's doing internally."*

### The from-scratch version

```
head <-> (most recent) <-> ... <-> (least recent) <-> tail
```

Two decisions carry the whole implementation:

**Why doubly linked.** Eviction removes the tail, and a "touch" unlinks a node from the *middle*.
Both need the node's predecessor in O(1), which a singly linked list cannot give you.

**Why sentinels.** A permanent `head` and `tail` node mean no branch ever handles "the list is
empty" or "this is the first element". Every unlink is the same four pointer assignments:

```python
def _unlink(self, node):
    prev, nxt = node.prev, node.next
    prev.next = nxt
    nxt.prev = prev
```

Without sentinels each of those lines needs a `None` check, and that is precisely where the bugs
live. Sentinels delete the bugs instead of handling them.

### The bug the interviewer is hunting for

```python
def _evict(self):
    lru = self._tail.prev
    self._unlink(lru)
    del self._map[lru.key]   # <-- the line people forget
```

Unlink from the list but leave the key in the dict, and the cache reports evicted keys as present,
hands back nodes no longer in the recency list, and **grows without bound** — an unbounded memory
leak wearing a cache's clothes. `case_eviction_removes_from_both_structures` inserts 50 keys into
a capacity-2 cache and asserts exactly 2 survive.

The invariant to state out loud: *every mutation touches both structures, and they are always the
same size.*

### Two subtleties worth naming

**An update is a use.** `put` on an existing key must refresh recency, and must not grow the
cache. Both are tested.

**`None` is a storable value.** `get` returning `None` cannot distinguish "stored `None`" from
"absent". That is why `__contains__` exists, and why `functools.lru_cache` uses a private sentinel
internally. Naming this ambiguity unprompted reads very well.

### How the spec verifies correctness

Beyond the targeted cases, `case_survives_a_long_mixed_workload` runs 2000 seeded random
operations against a deliberately slow, obviously-correct reference model (a Python list used as
an MRU order) and asserts the full key ordering matches after **every single operation**. That is
model-based testing, and mentioning the technique is itself a senior signal.

---

## Complexity

| Operation | Time | Why |
|---|---|---|
| `get` | O(1) | dict lookup + two pointer splices |
| `put` | O(1) | dict insert + splice, plus O(1) eviction |
| `__contains__` | O(1) | dict lookup |
| space | O(capacity) | one node + one dict entry per key |

`keys_mru_first()` is O(n) and exists only for tests and debugging.

---

## Follow-ups they will ask next

**"Make it thread-safe."**
Wrap `get` and `put` in a single `threading.Lock`. Note that `get` *mutates* (it reorders), so a
reader/writer lock buys nothing here — every operation is a writer. Under heavy contention, shard
the cache into N independent caches keyed by `hash(key) % N` to reduce lock contention.

**"Add a TTL."**
Store `(value, expires_at)` and treat an expired entry as a miss on read (lazy expiry). Lazy alone
lets expired-but-unread entries occupy capacity, so add a periodic sweep or a heap of expiry times
for eager eviction. See drill `03-ttl-cache`.

**"What about LFU?"**
LFU evicts the *least frequently* used, which needs a frequency counter plus buckets of equal
frequency to stay O(1). LRU adapts fast to changing workloads; LFU resists one-off scans but can
be poisoned by items that were popular once. Real systems often use W-TinyLFU or ARC to get both.

**"How does `functools.lru_cache` differ?"**
It is a *memoisation* decorator: keys are the function arguments, and it is implemented in C with
exactly this structure. Its gotchas are worth knowing — arguments must be hashable, `maxsize=None`
means unbounded (a common memory leak), and decorating a **method** keeps `self` in the key, so
the cache holds a strong reference to every instance and prevents them being garbage collected.

**"Now make it distributed."**
That is Redis, and the answer changes shape entirely: `maxmemory-policy allkeys-lru` gives you an
*approximated* LRU (Redis samples a handful of keys rather than maintaining a global order,
because a true global LRU across a shared-nothing cluster would need coordination on every read).
Then the real questions are cache stampede, invalidation, and consistency — see
`08-System-Design/08-caching-strategies-and-stampede.md`.

---

## Say it out loud

> An LRU needs O(1) lookup *and* O(1) recency updates, so I combine two structures: a dict from
> key to node for lookup, and a doubly linked list for ordering. Doubly linked because both
> eviction and touching a key require unlinking a node given only that node, which needs its
> predecessor. I use head and tail sentinels so no branch has to special-case an empty list —
> every splice is the same four assignments. `get` unlinks and pushes to the front; `put` does
> the same and evicts the node before the tail when it is over capacity. The bug to watch for is
> evicting from the list but not the dict, which turns the cache into an unbounded memory leak.
> In practice I would just use `OrderedDict` — `move_to_end` and `popitem(last=False)` are both
> O(1) and it is the same algorithm in C — or `functools.lru_cache` for memoisation, remembering
> that decorating a method pins every instance in memory.
