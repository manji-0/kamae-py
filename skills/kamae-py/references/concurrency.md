# Concurrency, the GIL, and Async Boundaries

<!-- constrained-by ./application-wiring.md -->
<!-- constrained-by ./state-transitions.md -->

Kamae Python assumes **asyncio** for I/O-bound application code: HTTP handlers, repository adapters, queue consumers. Pure domain transitions stay **synchronous**. This split keeps business rules easy to test without an event loop.

## Default Model

| Layer | Concurrency style | Why |
| --- | --- | --- |
| **Domain transitions** | Sync pure functions | No hidden scheduling; trivial unit tests |
| **Use cases** | `async def` when ports are async | Orchestrates I/O without blocking the loop |
| **Repository / HTTP adapters** | `async def` with async drivers | `asyncpg`, `httpx`, aiobotocore, etc. |
| **CPU-bound work** | `ProcessPoolExecutor` or worker queue | Python threads do not parallelize CPU due to the GIL |

```python
async def assign_driver_use_case(
    resolver: RequestResolver,
    store: RequestStore,
    request_id: UUID,
    driver_id: UUID,
    now: datetime,
) -> Result[EnRoute, AssignDriverError]:
    waiting = await resolver.find_waiting(request_id)
    if waiting is None:
        return Err(AssignDriverError.not_found(request_id))
    en_route = assign_driver(waiting, driver_id, now)  # sync pure transition
    await store.save_en_route(en_route, events=(...), ...)
    return Ok(en_route)
```

The transition runs in the caller's thread on the event loop. That is fine when it is fast. It is not fine when it performs heavy CPU work.

## The GIL in Practice

CPython's Global Interpreter Lock allows only one thread to execute Python bytecode at a time per process. Implications:

- **`asyncio`** excels when tasks wait on I/O. While one coroutine awaits a socket, others run.
- **`threading`** helps for **I/O-bound blocking libraries** without async support (some DB drivers, legacy SDKs). It does **not** speed up CPU-bound Python loops.
- **`multiprocessing` / `ProcessPoolExecutor`** is the default escape hatch for **CPU-bound** Python work: image processing, large aggregations, cryptographic operations on big payloads, ML inference in pure Python.

Do not run long CPU-bound Python functions directly inside `async def` use cases—they block the entire event loop and stall all concurrent requests.

## Offloading CPU-Bound Domain Work

Keep the **domain function sync**. Schedule it from the use case or infrastructure edge.

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

_executor = ProcessPoolExecutor(max_workers=4)


async def resize_proof_image_use_case(
    store: ImageStore,
    image_id: UUID,
    max_edge_px: int,
) -> Result[ResizedImage, ResizeError]:
    raw = await store.load_bytes(image_id)
    loop = asyncio.get_running_loop()
    try:
        resized = await loop.run_in_executor(
            _executor,
            resize_image_bytes,  # sync; CPU-bound; picklable top-level function
            raw,
            max_edge_px,
        )
    except ImageTooLarge as exc:
        return Err(ResizeError.too_large(image_id, str(exc)))
    await store.save_resized(image_id, resized)
    return Ok(resized)
```

Guidelines:

- Pass **plain data** (bytes, primitives, frozen Pydantic models) into worker processes—not open connections, ORM sessions, or locks.
- Worker functions should be **top-level** and picklable when using multiprocessing on POSIX and Windows.
- Prefer a **dedicated worker service** (Celery, RQ, ARQ, SQS consumer) when jobs are long, need retries, or must survive process restarts.
- Release the GIL inside **native extensions** (Pillow, numpy, some crypto libs). A sync call into native code may be acceptable on the event loop if documented and bounded—profile first.

## Threading vs Process Pool

| Approach | Good for | Avoid when |
| --- | --- | --- |
| `asyncio` alone | Network I/O, async DB | CPU-heavy Python loops in coroutines |
| `threading` / `run_in_executor` with default pool | Blocking I/O in legacy SDKs | CPU-bound Python (GIL contention) |
| `ProcessPoolExecutor` | CPU-bound pure Python | Functions that need shared mutable state or open DB handles |
| External worker queue | Long jobs, retry, backpressure | Sub-millisecond work where queue overhead dominates |

## Domain Layer and Non-Async Code

Domain modules should remain **importable without asyncio**. Rules:

1. Pure transitions are plain `def` functions.
2. Do not call `asyncio.run`, `get_event_loop`, or `await` inside `domain.py`.
3. If a port must expose sync and async variants, prefer **one async port** at the application boundary and implement sync adapters with `asyncio.to_thread` only at the infrastructure edge—not in domain code.
4. Time and randomness are injected as arguments (`now: datetime`, `rng: Random`), not read from ambient globals, so the same functions run in workers and tests.

## Framework Entrypoints

Wire executors and process pools at the **composition root** (FastAPI lifespan, Celery app factory), not as module-level side effects in domain packages.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.image_executor = ProcessPoolExecutor(max_workers=4)
    yield
    app.state.image_executor.shutdown(wait=True)
```

Read [`application-wiring.md`](./application-wiring.md) for port wiring and [`infrastructure-resilience.md`](./infrastructure-resilience.md) for timeouts and retries around slow workers.
