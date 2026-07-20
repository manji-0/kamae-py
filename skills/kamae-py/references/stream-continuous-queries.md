# Streams and Continuous Queries

<!-- constrained-by ./persistence-events.md -->
<!-- constrained-by ./aggregates.md -->
<!-- constrained-by ./service-boundaries.md -->

> **When to read:** Outbox relays, event subscriptions, CQRS projections, worker loops, or continuous change feeds.
> **Related:** [`persistence-events.md`](./persistence-events.md), [`aggregates.md`](./aggregates.md), [`service-boundaries.md`](./service-boundaries.md), [`concurrency.md`](./concurrency.md).

## Use Async Iterators for Event and Change Feeds

In event-sourced or CQRS designs, consumers often need a continuous feed of aggregate changes rather than a one-shot query. Model these feeds as async iterator ports (`AsyncIterator[T]` / `collections.abc.AsyncIterator`) at the boundary — not as ad-hoc `while True: sleep; poll` loops buried inside adapters without a testable surface.

```python
from collections.abc import AsyncIterator
from typing import Protocol


class AggregateEventSource(Protocol):
    def subscribe(
        self,
        aggregate_id: RequestId,
        after: EventSequence | None,
    ) -> AsyncIterator[DomainEvent]: ...
```

Keep domain transitions pure and synchronous with respect to business rules. Streams belong in read-side projections, outbox processors, and integration adapters that poll or subscribe to storage.

## Separate Command Path from Read Streams

| Concern | Shape | Notes |
| --- | --- | --- |
| Write use case | `async def -> Result[..., E]` | One command, one transaction boundary |
| Aggregate replay | `AsyncIterator[DomainEvent]` | Ordered events for one aggregate |
| Continuous query / projection | `AsyncIterator[ReadModelRow]` | Derived state; may lag the write model |
| Outbox dispatch | `AsyncIterator[OutboxRow]` | At-least-once delivery; handlers must be idempotent |

Do not expose an async iterator from a domain transition function. Emit events from the transition, persist them atomically, then let adapters expose the persisted log as a stream.

## Subscribe After Persisting

Start subscriptions from a durable cursor: event sequence, LSN, or `occurred_at` plus tie-breaker. Avoid in-memory broadcast that can drop events when a consumer reconnects.

```python
from pydantic import BaseModel, ConfigDict


class EventCursor(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    aggregate_id: UUID
    after_sequence: int


async def stream_pending(
    conn: asyncpg.Connection,
    *,
    batch_size: int = 50,
) -> AsyncIterator[OutboxRow]:
    rows = await conn.fetch(
        """
        SELECT id, payload, event_id, sequence
        FROM outbox
        WHERE published_at IS NULL
        ORDER BY sequence
        LIMIT $1
        FOR UPDATE SKIP LOCKED
        """,
        batch_size,
    )
    for row in rows:
        yield OutboxRow.from_record(row)
```

When a projection catches up, store the checkpoint in the same persistence technology as the projection table so restarts resume safely. Align outbox relay details with [`persistence-events.md`](./persistence-events.md#outbox-relay-and-at-least-once-delivery).

## Handle Backpressure and Cancellation

Streams that never apply backpressure can exhaust memory or duplicate work when consumers are slow.

- Prefer bounded queues (`asyncio.Queue(maxsize=...)`) between storage polling and handlers when bridging tasks.
- Propagate cancellation: when a task or HTTP request is cancelled, stop polling and release DB cursors or locks (`asyncio.CancelledError`, `async with` contexts).
- Treat iterator errors as terminal for that subscription unless the adapter documents retry semantics.

```python
async def bridge(
    source: AggregateEventSource,
    request_id: RequestId,
    cursor: EventSequence | None,
    queue: asyncio.Queue[DomainEvent | None],
) -> None:
    try:
        async for event in source.subscribe(request_id, cursor):
            await queue.put(event)
    finally:
        await queue.put(None)  # sentinel: producer finished or cancelled
```

For CPU-bound projection work that would block the event loop, offload at the composition root — see [`concurrency.md`](./concurrency.md).

## Projections Must Be Deterministic and Idempotent

Continuous queries rebuild read models from event streams. Each handler should:

1. Parse the event payload into a typed domain or integration event.
2. Apply the update idempotently using event ID or `(aggregate_id, sequence)`.
3. Skip or dead-letter events with unknown type/version according to the schema evolution policy in [`service-boundaries.md`](./service-boundaries.md#json-and-protobuf-schema-evolution).

```python
async def apply_event(
    store: ProjectionStore,
    event: StoredEvent,
) -> Result[None, ProjectionError]:
    if await store.already_applied(event.id):
        return Ok(None)

    match event.kind:
        case "driver_assigned":
            await store.mark_en_route(event.payload)
        case "unknown":
            return Err(
                ProjectionError.unsupported(
                    version=event.schema_version,
                    name=event.event_type,
                )
            )

    await store.record_checkpoint(event.id)
    return Ok(None)
```

## Keep CQRS Boundaries Explicit

Read models may denormalize for queries, but they must not become a second write model. Cross-aggregate updates in a projection should react to events, not call write-side transition functions or mutate other aggregates directly.

For transaction scope on the write side, optimistic versioning, and outbox atomicity, see [`aggregates.md`](./aggregates.md) and [`persistence-events.md`](./persistence-events.md).

## Worker Runtimes

Celery, ARQ, RQ, Dramatiq, and custom asyncio workers are composition-root hosts for stream consumers — not domain modules.

| Host | Role | Keep in infrastructure |
| --- | --- | --- |
| Celery / Dramatiq task | Pull message → validate DTO → call use case or projection | Retries, acks, routing keys |
| ARQ / asyncio worker | Poll outbox or broker → async iterator consumer | Lease / SKIP LOCKED, heartbeats |
| Kafka / Redis Streams consumer | Partition cursor → typed handler | Offset commit after successful idempotent apply |

Do not import Celery or broker clients from `domain` packages. Wire them at the composition root beside FastAPI lifespan or worker app factories — see [`application-wiring.md`](./application-wiring.md).

## Detection Hints

When code introduces `AsyncIterator` event ports, outbox pollers, projection tables, Celery/ARQ consumers, `aiokafka`, or Redis Streams, prefer typed async-iterator ports over opaque sleep loops. Load this guide with persistence and service-boundary references when the diff touches subscriptions, projections, or outbox processors.
