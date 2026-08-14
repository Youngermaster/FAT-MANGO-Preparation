# Big-O of Python Builtins — Measured

> **Prompt as you will hear it:** *"What's the complexity of that?"* — usually asked about code you
> have just written, five seconds after you wrote it.

Reciting a table is worth little. Being able to say *"I've measured it — set membership is ~770×
faster at this size"* is worth a lot, and it changes how you write code without thinking about it.

---

## Run it

```bash
uv run python 03-Algorithms-And-Data-Structures/00-complexity-cheatsheet/complexity.py
uv run pytest 03-Algorithms-And-Data-Structures     # 14 tests
```

Every number is timed on your machine. **Read the growth column, not the absolute times** — the
shape is the lesson.

---

## The measurements

```
MEMBERSHIP: `x in list` vs `x in set`     n=1k     n=10k    n=100k   |  growth
  x in list      -> O(n)                                             |  ~10x per 10x of n
  x in set       -> O(1)                                             |  ~1.0x

FRONT OF SEQUENCE                        n=10k    n=100k             |  growth
  list.pop(0)    -> O(n)                  1.72     19.56             |   11.4x
  deque.popleft()-> O(1)                  0.02      0.02             |    1.0x

TOP-K (k=10)                             n=10k    n=100k             |  growth
  sorted(xs)[:10]-> O(n log n)          680.29   9415.13             |   13.8x
  nlargest(10,xs)-> O(n log k)          126.14   1152.30             |    9.1x

THE PRACTICAL VERSION: filtering one list against another
  membership against a list     281.19 ms
  membership against a set        0.37 ms   (770x faster)
```

That last block is the one to remember. One line — `allowed = set(allowed)` — and it is a
different complexity class.

---

## The table

| Operation | Complexity | Note |
|---|---|---|
| `list` index / `append` | O(1) amortised | |
| `list.insert(0, x)` / `pop(0)` | **O(n)** | shifts everything; use `deque` |
| `x in list` | **O(n)** | the most common accidental O(n·m) |
| `x in set` / `x in dict` | O(1) average | O(n) worst case with adversarial hashes |
| `deque.appendleft` / `popleft` | O(1) | no O(1) random access, though |
| `sorted()` / `.sort()` | O(n log n) | Timsort, **stable** |
| `heapq.heappush` / `heappop` | O(log n) | `heapify` is O(n) |
| `bisect` search | O(log n) | but `insort` is O(n) — the shift dominates |
| `a[i:j]` | O(j−i) | **copies** |
| `s += t` in a loop | O(n²) in principle | see below |
| `heapq.nlargest(k, xs)` | O(n log k) | beats `sorted()[:k]` when k ≪ n |

---

## The string-concatenation subtlety

The table says `+=` in a loop is O(n²). **The measurement says otherwise** — growth comes out near
4×, not 16×.

That is not an error in the measurement, and this is the more interesting answer:

> CPython has an **in-place realloc optimisation** that applies when the target string's refcount
> is 1, so the loop often behaves *linearly* — just with a much larger constant (`join` is still
> ~10× faster).

Why you should still never do it: the optimisation is a **CPython implementation detail**. It does
not apply on PyPy, and it silently stops applying the moment anything else holds a reference to
the string. So `+=` in a loop is a **latent O(n²)** that passes review, benchmarks fine, and
degrades later under conditions you did not change.

Being able to say *"the naive answer is O(n²), CPython usually optimises it away, and that is
exactly why it is dangerous"* is a much better answer than either half alone.

---

## The stdlib traps, each with a test

| Trap | What happens |
|---|---|
| **`heapq` is a min-heap** | `heappop` gives the *smallest*. Negate values for a max-heap. |
| **Heap of tuples needs a tiebreaker** | Equal priorities force Python to compare the payloads → `TypeError` on anything unorderable. Push `(priority, counter, item)`. |
| **`groupby` needs sorted input** | It groups *consecutive* equal keys. Unsorted input silently fragments groups — no error, just wrong answers. |
| **`defaultdict` creates on read** | Merely *looking at* a missing key inserts it. `if d[k]:` grows the dict. |
| **`dict` is ordered but is not `OrderedDict`** | Insertion order is guaranteed since 3.7, but there is no `move_to_end` and no O(1) pop-from-front — which is exactly why an LRU uses `OrderedDict`. |
| **Slicing copies** | `a[1:]` inside a recursion turns O(n) into O(n²). Pass indices instead. |
| **`Counter` does arithmetic** | `a - b` drops non-positive counts; `a & b` takes the minimum. Handy and easy to misread. |
| **`deque(maxlen=n)`** | A ring buffer — appending past the limit silently drops the oldest. Useful for sliding windows, surprising if unintended. |

---

## Why this matters more than the algorithm

In a backend interview, the complexity mistakes that actually appear are not exotic:

- a membership test against a list inside a loop → accidental O(n·m)
- `list.pop(0)` as a BFS queue → accidental O(n²)
- `sorted(...)[:10]` over a million rows when `nlargest` would do
- slicing inside recursion

None of those require knowing an algorithm. They require knowing what the builtins cost. That is
why this page exists before the pattern folders.

---

## Say it out loud

> The ones I actually watch for are: membership against a list is O(n), so a lookup inside a loop
> is accidentally quadratic — converting to a set is a one-line fix and here it was about 700×
> faster. `list.pop(0)` shifts every element, so a BFS queue should be a `deque`. Slicing copies
> rather than viewing, so `a[1:]` inside a recursion changes the complexity class. And for top-K I
> use `heapq.nlargest`, which is O(n log k) instead of sorting the 99.99% I am about to discard.
> Sorting is Timsort — O(n log n) and stable, which means I can sort by a secondary key first and
> the ordering survives. Dicts have been insertion-ordered since 3.7 but they still lack
> `move_to_end`, which is why an LRU cache reaches for `OrderedDict`.
