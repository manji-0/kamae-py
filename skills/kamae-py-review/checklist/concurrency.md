# Concurrency Checklist

Reference: [`../../kamae-py/references/concurrency.md`](../../kamae-py/references/concurrency.md).

## 15.1 Is CPU-bound domain work kept off the event loop? - High

Flag blocking ORM calls, file I/O, heavy parsing, or CPU-bound loops inside `async def` handlers or use cases without `asyncio.to_thread`, executors, or an explicit sync boundary.

## 15.2 Is shared mutable state avoided in domain code? - Medium

Flag module-level mutable caches, globals, or singletons used by transitions or use cases when explicit arguments or ports would make behavior testable.

## 15.3 Are process/thread pools scoped and justified? - Medium

Flag broad `ProcessPoolExecutor` usage for small pure transitions, or pools created per request without lifecycle management.

## 15.4 Are locks and sessions scoped correctly? - High

Flag database sessions, ORM identity maps, or locks shared across concurrent tasks without clear ownership or transaction boundaries.

Cross-check [`error-handling.md`](./error-handling.md) and [`aggregates.md`](./aggregates.md) for await/lock interactions.
