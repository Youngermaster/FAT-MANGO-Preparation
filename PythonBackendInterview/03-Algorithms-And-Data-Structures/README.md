# Algorithms & Data Structures

Backend interviews at consultancies are **pattern-recognition** interviews, not competitive
programming. Expect Easy–Medium problems, and expect the interviewer to care more about *how you
choose the data structure* than about squeezing out the optimal constant factor.

Two things score disproportionately here, and neither is the algorithm:

1. **Standard-library fluency.** Reaching for `Counter`, `defaultdict`, `deque`, `heapq`, `bisect`
   is the clearest "senior Python" tell in a coding round.
2. **Naming the backend use case.** Top-K is a leaderboard. Topological sort is migration
   ordering. Intervals are scheduling. Saying that turns a puzzle answer into an engineering
   answer.

---

## Contents

| Folder | Pattern | Backend framing |
|---|---|---|
| [`00-complexity-cheatsheet`](00-complexity-cheatsheet/) | Big-O of Python builtins | why `in list` is the bug |
| [`01-hashmaps-and-counting`](01-hashmaps-and-counting/) | `Counter`, `defaultdict`, prefix sums | log analysis, dedup, top-K |

Each folder follows the repo convention: `README.md` (problem, why it is asked, walkthrough,
follow-ups, "say it out loud"), a solution module, and a test suite.

---

## The complexity table to know cold

This is the single highest-value thing in the section, because it turns up as a *correction* to
code you have just written.

| Operation | Complexity | Note |
|---|---|---|
| `list` index, `append` | O(1) amortised | |
| `list.insert(0, x)`, `pop(0)` | **O(n)** | use `deque` |
| `x in list` | **O(n)** | the most common accidental O(n·m) |
| `x in set` / `x in dict` | O(1) average | O(n) worst case with adversarial hashes |
| `dict` get/set/del | O(1) average | insertion-ordered since 3.7 |
| `deque.appendleft/popleft` | O(1) | |
| `sorted()` / `list.sort()` | O(n log n) | Timsort, **stable** |
| `heapq.heappush/heappop` | O(log n) | `heapify` is O(n) |
| `bisect.*` search | O(log n) | but `insort` is O(n) — the list shift dominates |
| `s1 + s2` in a loop | **O(n²)** | strings are immutable; use `"".join` |
| `a[i:j]` | O(j−i) | slicing **copies** |
| `min`/`max`/`sum` | O(n) | |
| `heapq.nlargest(k, xs)` | O(n log k) | beats `sorted(xs)[:k]` when k ≪ n |

---

## The stdlib toolkit

| Tool | Use it for | Gotcha |
|---|---|---|
| `collections.Counter` | frequency counting, `most_common(k)` | supports `+ - & \|` arithmetic |
| `collections.defaultdict` | grouping, adjacency lists | reading a missing key **creates** it |
| `collections.deque` | BFS queues, sliding windows, ring buffers (`maxlen`) | no O(1) random access |
| `collections.OrderedDict` | LRU (`move_to_end`, `popitem(last=False)`) | plain `dict` has neither |
| `heapq` | top-K, priority queues, merging streams | **min-heap only** — negate for max |
| `bisect` | binary search on sorted data | `insort` is O(n) |
| `itertools` | `groupby`, `accumulate`, `chain`, `pairwise`, `batched` (3.12+) | **`groupby` needs sorted input** |
| `functools` | `cache`/`lru_cache` for memoised DP, `reduce`, `partial` | args must be hashable |

Two gotchas that catch people out loud:

- **`heapq` is a min-heap.** For a max-heap, push `-value`, or tuples `(-priority, tiebreak, item)`
  — and include a tiebreaker so Python never has to compare the payload objects, which raises
  `TypeError` on anything unorderable.
- **`itertools.groupby` only groups *consecutive* equal keys.** Unsorted input silently produces
  fragmented groups. Sort first, or use `defaultdict`.

---

## Patterns, and where each shows up in a backend

| Pattern | Signal in the problem | Real system |
|---|---|---|
| Hashmap / counting | "how many", "duplicates", "most frequent" | log analysis, dedup, rate counters |
| Two pointers | sorted array, pair/triple summing to a target | merging sorted streams |
| Sliding window | "contiguous subarray/substring", "at most K" | **rate limiting**, moving averages |
| Prefix sums | repeated range queries, "subarray summing to K" | time-series rollups, billing periods |
| Heap / top-K | "K largest/smallest", "median of a stream" | leaderboards, k-nearest, `nlargest` over logs |
| Intervals | start/end pairs, overlaps, merging | scheduling, "how many servers do I need" |
| Binary search | sorted input, or "minimum X that works" | **binary search on the answer** — sizing a pool |
| BFS / DFS | grids, graphs, shortest unweighted path | dependency graphs, blast-radius analysis |
| Topological sort | "order respecting dependencies" | **migration ordering**, DAG task scheduling, build systems |
| Monotonic stack | "next greater element" | streaming maxima |
| Design (LRU, trie, rate limiter) | "implement a cache/limiter" | caching, autocomplete, quotas |

---

## How to run a problem, out loud

1. **Restate it** and give one example.
2. **Ask about the input** — size, sorted, duplicates, negative numbers, empty, Unicode.
3. **State the brute force and its complexity.** Never skip this; it proves you understand the
   problem before optimising, and it gives you something working to fall back on.
4. **Name the pattern** and the target complexity: *"the repeated lookup is the bottleneck, so a
   hash set makes it O(n)."*
5. **Write it**, narrating sparsely.
6. **Trace one example by hand**, then an edge case.
7. **State the complexity** and what you would change with more time.

Talking through step 3 and 4 is where the points are. A candidate who says *"brute force is O(n²)
because `in` on a list is O(n); a set makes membership O(1)"* has already demonstrated more than
the finished code will.

---

## Related material elsewhere in this repo

The design-flavoured problems that get asked most often for backend roles live in the drills,
because they double as live-coding tasks:

- **LRU cache** → [`04-Live-Coding-Drills/02-lru-cache-from-scratch`](../04-Live-Coding-Drills/02-lru-cache-from-scratch/)
- **Nested-structure recursion** → [`04-Live-Coding-Drills/03-flatten-nested-dict`](../04-Live-Coding-Drills/03-flatten-nested-dict/)
- **Bounded fan-out / worker pools** → [`02-Async-And-Concurrency/06-semaphores-and-concurrency-limits`](../02-Async-And-Concurrency/06-semaphores-and-concurrency-limits/)

And your existing `LeetCode/` folder at the repo root already covers a range of the classic
problems — this section is about the *patterns and the Python*, not about re-solving them.
