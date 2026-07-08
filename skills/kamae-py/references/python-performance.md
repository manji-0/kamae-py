# Python Performance and Write Style

> **When to read:** Hot paths, list/batch processing, repository loops, serialization outside Pydantic, or code where the same work runs per request, per row, or per event.
> **Related:** [`pydantic-performance.md`](./pydantic-performance.md), [`concurrency.md`](./concurrency.md), [`state-transitions.md`](./state-transitions.md), [`persistence-events.md`](./persistence-events.md).

<!-- constrained-by ./pydantic-performance.md -->
<!-- constrained-by ./concurrency.md -->

Python makes it easy to write correct code that is quietly expensive. In Kamae Python, most domain transitions should stay cheap and synchronous; performance work belongs on boundaries, repositories, and batch jobs after measurement—not on micro-optimizing every helper.

## Measure Before Rewriting

Profile realistic workloads before changing style:

1. Use `py-spy`, `cProfile`, or your APM on a load test that matches production request mix.
2. Confirm the bottleneck is Python execution, not SQL round-trips, network latency, or oversized logging.
3. Fix algorithmic and I/O problems first. A better index or one fewer query usually beats a faster loop.

If validation dominates, read [`pydantic-performance.md`](./pydantic-performance.md). If the event loop stalls on CPU work, read [`concurrency.md`](./concurrency.md).

## Where Style Matters in Kamae Code

| Layer | Performance stance |
| --- | --- |
| Pure transitions | Keep O(1) or O(fields); no I/O, parsing, or hidden scans |
| Use cases | One repository round-trip per aggregate when possible; batch at ports |
| Repositories / mappers | Avoid N+1 queries and per-row adapter creation |
| Boundaries | Parse once; pass validated domain objects inward |
| Tests | Reuse fixtures; do not re-parse identical payloads thousands of times |

Domain clarity comes first. Optimize only where profiling shows repeated work on a hot path.

## Data Structures and Membership

Choose the structure that matches how data is accessed.

| Need | Prefer | Avoid on hot paths |
| --- | --- | --- |
| Frequent membership test | `set` / `frozenset` | `x in long_list` |
| Keyed lookup | `dict` | Scan a list of pairs |
| Stable insertion order + keyed lookup | `dict` (3.7+) | Parallel list + dict |
| Queue ends | `collections.deque` | `list.pop(0)` |
| Counting | `collections.Counter` | Manual dict increments in nested loops |
| Sorted inserts / ranges | `bisect` on a sorted list | Resorting every request |

```python
# Slow: O(n) per check inside a loop
allowed_statuses = ["waiting", "en_route", "in_trip"]
for row in rows:
    if row["status"] in allowed_statuses:
        ...

# Fast enough for thousands of rows
ALLOWED_STATUSES = frozenset({"waiting", "en_route", "in_trip"})
for row in rows:
    if row["status"] in ALLOWED_STATUSES:
        ...
```

Build lookup tables once at module scope or process startup when the reference data is stable.

## Loops, Comprehensions, and Generators

List comprehensions and generator expressions are usually as fast as an explicit `for` loop and often clearer. The expensive part is the **work inside** the loop, not whether you used a comprehension.

```python
# Materializes every row in memory
ids = [row["id"] for row in rows]

# Streams when you only need one pass
total = sum(price * qty for price, qty in line_items)
```

Guidelines:

- Use generators (`yield`, generator expressions) when processing streams or large files line by line.
- Do not wrap a generator in `list()` unless a second pass is required.
- Hoist invariant work out of loops: regex compilation, `TypeAdapter` creation, `json` decoder setup, compiled `re` patterns, and constant `frozenset`/`dict` maps belong outside the loop.

```python
# Hoist adapter and allowed set
RowAdapter = TypeAdapter(RequestRow)
ACTIVE = frozenset({"waiting", "en_route"})

def active_rows(rows: Iterable[Mapping[str, object]]) -> list[RequestRow]:
    return [RowAdapter.validate_python(row) for row in rows if row.get("status") in ACTIVE]
```

Avoid nested loops that re-scan collections. Pre-index related data:

```python
# Slow: O(n * m)
for order in orders:
    for line in all_lines:
        if line.order_id == order.id:
            ...

# Better: O(n + m)
lines_by_order: dict[UUID, list[Line]] = {}
for line in all_lines:
    lines_by_order.setdefault(line.order_id, []).append(line)
for order in orders:
    for line in lines_by_order.get(order.id, ()):
        ...
```

## Attribute and Name Lookup

Python resolves local names faster than globals or attributes. In tight inner loops, bind frequently used callables or methods to a local variable when profiling shows it matters.

```python
def normalize_many(values: Iterable[str]) -> list[str]:
    lower = str.lower  # local binding; optional micro-optimization
    return [lower(value) for value in values]
```

Prefer functions and data over deep attribute chains in hot paths:

```python
# Harder to read; repeats lookups
for item in items:
    item.context.metrics.counter.labels(item.kind).inc()

# Clearer boundary: compute once per item
for item in items:
    record_metric(item.kind)
```

Do not sacrifice readability across the whole codebase for nanoseconds in cold paths.

## Strings, Bytes, and Serialization

| Pattern | Cost | Prefer |
| --- | --- | --- |
| `s += piece` in a loop | Quadratic copies | `"".join(parts)` or `io.StringIO` |
| Repeated `str(x)` on the same object | Extra allocations | Format once; cache when logging |
| `json.dumps` per row in a batch export | High | Batch encode; consider `orjson` at infrastructure edge |
| `model_dump()` on large states for logs | High | Log identifiers and `kind` only |

```python
chunks: list[str] = []
for part in parts:
    chunks.append(render(part))
message = "".join(chunks)
```

For HTTP JSON at scale, compare `validate_json`, `orjson`, and msgspec on **your** payload sizes. Keep domain models on Pydantic; faster serializers belong at the wire edge. See [`pydantic-performance.md`](./pydantic-performance.md#msgspec-boundary--pydantic-domain-pipeline).

## Copies, Views, and Memory

Unnecessary copies multiply memory and GC pressure.

- Prefer passing immutable domain states through layers instead of `dict(model)` conversions on every hop.
- Use `list(seq)` only when a real independent copy is required.
- Avoid `copy.deepcopy` in request paths unless mutating shared graphs is unavoidable.
- Slicing (`seq[start:stop]`) creates a shallow copy of a list; for read-only scans, iterate indices or use `itertools.islice`.

Frozen Pydantic models and small `NamedTuple`/`dataclass(frozen=True)` values are cheap to pass by reference.

## Standard Library Tools That Scale

Reach for stdlib algorithms before hand-rolling scans:

| Module | Use for |
| --- | --- |
| `itertools` | Chaining, grouping, sliding windows without intermediate lists |
| `functools.cache` / `lru_cache` | Pure parse helpers on immutable reference data |
| `heapq` | Top-k without full sort |
| `bisect` | Maintaining sorted sequences |
| `collections.defaultdict` | Grouping without repeated `if key not in dict` |
| `enum.Enum` | Stable constants with fast identity checks |

```python
from itertools import batched

def publish_in_chunks(events: Sequence[DomainEvent], size: int) -> None:
    for chunk in batched(events, size):  # Python 3.12+
        publisher.send_batch(chunk)
```

## Lazy vs Eager Work

Defer work until it is needed:

- Parse boundary input once at the edge; pass domain types inward.
- Build error detail strings only on failure branches.
- Open files and network connections inside the code path that needs them, not in module import side effects.

Eager work belongs where invariants are enforced: boundary validation, migration scripts, and test fixtures that must fail fast.

## Caching Rules

| Cache | OK when | Not OK when |
| --- | --- | --- |
| Module-level `TypeAdapter` | Schema is fixed | Dynamic schema per tenant without version key |
| `functools.cache` on pure config parsers | Input is hashable and immutable | External data that can change without process restart |
| Read-model cache (Redis, LRU) | Keyed by version/ETag; invalidated on write | Raw dicts from HTTP treated as domain objects |

Never cache unvalidated external payloads as domain truth. Document TTL or version keys.

## Repository and Batch Patterns

Most backend slowness is I/O shape, not Python syntax.

1. **N+1 queries:** load related rows in one query or a bounded number of queries; map in Python once.
2. **Per-row adapter creation:** reuse module-level adapters and mappers (see [`orm-adapters.md`](./orm-adapters.md)).
3. **Re-validation:** row DTO once, `model_construct` into domain only on trusted paths ([`pydantic-performance.md`](./pydantic-performance.md#when-model_construct-is-acceptable)).
4. **Large list endpoints:** return narrow read DTOs; do not hydrate full aggregate unions for table views.

```python
# Port expresses batch intent
class RequestReader(Protocol):
    async def list_waiting_ids(self, limit: int) -> Sequence[UUID]: ...
    async def load_waiting_many(self, ids: Sequence[UUID]) -> Sequence[Waiting]: ...
```

## Keep Transitions Cheap

Pure transition functions should allocate one new frozen model and return. They should not:

- Re-parse JSON or re-run `TypeAdapter` on data already typed as domain state
- Scan unbounded collections when an indexed lookup exists
- Call logging formatters that stringify entire aggregates

If a transition needs derived data, compute it from fields already on the input state or pass it as an explicit argument from the use case.

## What Not to Micro-optimize

Skip style debates that do not show up in profiles:

- `for` vs list comprehension when the body is dominated by I/O
- `match` vs `if/elif` for small discriminated unions
- Tuple vs small frozen dataclass in cold configuration code
- Premature `__slots__` on rarely instantiated classes

Escalate to faster libraries, batching, or process offload only after the hot path is identified.

## Profiling Checklist

Before landing a performance-focused change:

1. Capture baseline latency and CPU with realistic data volume.
2. Note whether the fix changes asymptotic complexity, constant factors, or I/O count.
3. Add or extend a test that would fail if the batching/map pre-index regresses to per-item queries.
4. Record the profiling evidence in the PR or commit message when the style is non-obvious.

Read [`quality-gates.md`](./quality-gates.md) before finishing; performance shortcuts must not weaken boundary validation or domain invariants.
