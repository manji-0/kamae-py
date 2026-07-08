# Python Performance Checklist

Reference: [`../../kamae-py/references/python-performance.md`](../../kamae-py/references/python-performance.md).

## 21.1 Is the hot path identified by evidence? - Low

Flag performance-driven rewrites without profiling, query counts, or realistic load data.

Do not flag clear algorithmic fixes such as replacing repeated linear scans with a `dict`/`set` index when complexity is obviously worse.

## 21.2 Do loops avoid repeated invariant work? - Medium

Flag per-iteration creation of parsers, adapters, regexes, or large temporary collections on paths that run per row, per message, or per request.

Suggest hoisting module-level constants, batch ports, or generators when the diff introduces nested scans or `list()` materialization on streams.

## 21.3 Are repository and batch boundaries shaped efficiently? - High

Flag N+1 query patterns, per-row round-trips, or list endpoints that hydrate full aggregate unions when a narrow read DTO would suffice.

Cross-check [`persistence-events.md`](./persistence-events.md) and [`orm-adapters.md`](./orm-adapters.md) when persistence code changes.

## 21.4 Do shortcuts preserve domain invariants? - High

Flag caching of unvalidated external data, skipped validation on hot paths, or `deepcopy`/`model_construct` used to bypass invariants for speed.

Performance work must not weaken boundary parsing or frozen-state guarantees.
