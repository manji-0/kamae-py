# Persistence and Events

> **When to read:** Designing repositories, transactions, outbox records, idempotent commands, optimistic locking, or event payloads.
> **Related:** [`aggregates.md`](./aggregates.md), [`orm-adapters.md`](./orm-adapters.md), [`infrastructure-resilience.md`](./infrastructure-resilience.md), [`boundary-defense.md`](./boundary-defense.md), [`service-boundaries.md`](./service-boundaries.md), [`stream-continuous-queries.md`](./stream-continuous-queries.md).


Read [`aggregates.md`](./aggregates.md) for aggregate roots, one-command consistency boundaries, and who owns transactions.

## Keep Repository Protocols Small

**Canonical** `RequestResolver` and `RequestStore` definitions for optimistic locking, idempotency, and event persistence:

Repository protocols should express use-case needs, not ORM convenience. Split read and write interfaces when it keeps callers from depending on broad CRUD operations.

```python
class RequestResolver(Protocol):
    async def find_waiting(self, request_id: UUID) -> Waiting | None: ...


class RequestStore(Protocol):
    async def save_en_route(
        self,
        state: EnRoute,
        events: tuple[DriverAssigned, ...],
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> None: ...
```

Adapters can use SQLAlchemy, SQLModel, asyncpg, psycopg, Django ORM, or another tool internally. Do not let that tool's model shape become the domain API by default. Read [`orm-adapters.md`](./orm-adapters.md) for mapper implementations between ORM entities and Pydantic domain states.

## Optimistic Locking

<!-- constrained-by ./aggregates.md#optimistic-vs-pessimistic-concurrency -->

**Checklist mapping (12.1, 12.4):** Load version with state, apply pure transition, save with `expected_version`. Database `UPDATE` must be conditional.

### State and version column

Include a monotonic `version` on persisted aggregate rows (or derive from an `updated_at` token only if the database guarantees uniqueness under concurrency—which is rare).

```python
class Waiting(DomainModel):
    kind: Literal["waiting"] = "waiting"
    request_id: UUID
    tenant_id: UUID
    passenger_id: UUID
    created_at: datetime
    version: int  # starts at 1 on create; increment on each successful save
```

### Repository save with version check

```python
class VersionConflict(Exception):
    def __init__(self, aggregate_id: UUID, expected: int, actual: int | None) -> None:
        self.aggregate_id = aggregate_id
        self.expected = expected
        self.actual = actual


async def save_en_route(
    conn: asyncpg.Connection,
    state: EnRoute,
    events: tuple[DriverAssigned, ...],
    *,
    expected_version: int,
    idempotency_key: str,
) -> None:
    async with conn.transaction():
        row = await conn.fetchrow(
            """
            UPDATE taxi_requests
            SET kind = $2,
                driver_id = $3,
                assigned_at = $4,
                version = version + 1
            WHERE request_id = $1
              AND version = $5
              AND tenant_id = $6
            RETURNING version
            """,
            state.request_id,
            state.kind,
            state.driver_id,
            state.assigned_at,
            expected_version,
            state.tenant_id,
        )
        if row is None:
            current = await conn.fetchval(
                "SELECT version FROM taxi_requests WHERE request_id = $1",
                state.request_id,
            )
            raise VersionConflict(state.request_id, expected_version, current)

        for event in events:
            await insert_outbox_event(conn, event, idempotency_key=idempotency_key)
```

Map `VersionConflict` to `Err` in the use case. The client may retry with a fresh read. Do not retry blindly inside the repository.

### Use-case flow

```python
waiting = await resolver.find_waiting(request_id)
if waiting is None:
    return Err(RequestNotFound(...))

en_route, events = assign_driver(waiting, driver_id, now=utc_now())

try:
    await store.save_en_route(
        en_route,
        events,
        expected_version=waiting.version,
        idempotency_key=idempotency_key,
    )
except VersionConflict:
    return Err(ConcurrentModification(request_id=request_id))

return Ok(en_route)
```

Pessimistic locking (`SELECT … FOR UPDATE`) belongs in adapters for inventory or balance holds. Read [`aggregates.md`](./aggregates.md#optimistic-vs-pessimistic-concurrency).

## Transaction Context Managers

The repository adapter owns the transaction. Use driver-native context managers so commit/rollback stay correct under exceptions.

### asyncpg

```python
import asyncpg


class AsyncpgUnitOfWork:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._conn: asyncpg.Connection | None = None
        self._tx: asyncpg.transaction.Transaction | None = None

    async def __aenter__(self) -> asyncpg.Connection:
        self._conn = await self._pool.acquire()
        self._tx = self._conn.transaction()
        await self._tx.start()
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> None:
        assert self._conn is not None and self._tx is not None
        try:
            if exc_type is None:
                await self._tx.commit()
            else:
                await self._tx.rollback()
        finally:
            await self._pool.release(self._conn)


async def save_with_outbox(pool: asyncpg.Pool, state: EnRoute, events: tuple[DriverAssigned, ...], *, expected_version: int) -> None:
    async with AsyncpgUnitOfWork(pool) as conn:
        await save_en_route(conn, state, events, expected_version=expected_version, idempotency_key=...)
```

### psycopg 3

```python
from psycopg import AsyncConnection
from psycopg.rows import dict_row


async def save_with_outbox_psycopg(conn: AsyncConnection, state: EnRoute, events: tuple[DriverAssigned, ...], *, expected_version: int) -> None:
    async with conn.transaction():
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                UPDATE taxi_requests
                SET kind = %(kind)s, driver_id = %(driver_id)s, version = version + 1
                WHERE request_id = %(request_id)s AND version = %(expected_version)s
                RETURNING version
                """,
                {**state.model_dump(mode="python"), "expected_version": expected_version},
            )
            if cur.rowcount != 1:
                raise VersionConflict(...)
        for event in events:
            await insert_outbox_event_psycopg(conn, event)
```

One `async with conn.transaction()` block wraps state update and outbox inserts. Do not commit between them.

## Persist State and Events Atomically

When a transition emits domain events, write the aggregate state and outbox/event rows in the same transaction. Avoid APIs that let callers save state and events separately.

```python
async with transaction:
    await update_request_state(state, expected_version=expected_version)
    await insert_outbox_events(events)
```

The outbox worker can publish events after commit. Publishing directly inside the transaction or before the state commit risks duplicate or missing notifications.

## Outbox Relay and At-Least-Once Delivery

<!-- constrained-by ./infrastructure-resilience.md -->

Message brokers typically provide **at-least-once** delivery. Design for idempotent consumers and dedupe on the publisher side.

### Outbox table shape

```python
class OutboxRow(BaseModel):
    id: UUID
    aggregate_id: UUID
    event_name: str
    event_version: int
    payload: dict[str, object]
    idempotency_key: str
    created_at: datetime
    published_at: datetime | None = None
```

### Worker pattern

```text
loop:
  SELECT ... FROM outbox WHERE published_at IS NULL ORDER BY created_at LIMIT N FOR UPDATE SKIP LOCKED
  publish each row to broker
  UPDATE outbox SET published_at = now() WHERE id = ...
```

Guarantees:

1. **State and outbox rows commit together** — consumers never see events for uncommitted state.
2. **Publish after commit** — worker reads only committed rows.
3. **At-least-once publish** — crash after publish but before `published_at` update causes duplicate delivery; consumers dedupe by `event_id`.
4. **`event_id` unique** — insert `UNIQUE(event_id)` on outbox or consumer inbox table.
5. **Idempotent handler** — `INSERT INTO processed_events (event_id) ON CONFLICT DO NOTHING` before side effects.

```python
async def relay_outbox_batch(conn: asyncpg.Connection, publisher: EventPublisher) -> int:
    rows = await conn.fetch(
        """
        SELECT id, payload, event_id
        FROM outbox
        WHERE published_at IS NULL
        ORDER BY created_at
        LIMIT 50
        FOR UPDATE SKIP LOCKED
        """
    )
    count = 0
    for row in rows:
        await publisher.publish(row["payload"])
        await conn.execute(
            "UPDATE outbox SET published_at = now() WHERE id = $1",
            row["id"],
        )
        count += 1
    return count
```

Retry publish failures with backoff (`infrastructure-resilience.md`). Do not delete outbox rows until retention policy requires it.

## Mirror Critical Invariants in the Database

Use database constraints for invariants the database can enforce: uniqueness, tenant ownership foreign keys, non-negative balances, valid lifecycle states, idempotency keys, and event uniqueness.

Application checks are still needed for good errors and domain clarity, but they are not enough under concurrency.

```sql
ALTER TABLE taxi_requests
    ADD CONSTRAINT taxi_requests_version_positive CHECK (version > 0);

CREATE UNIQUE INDEX outbox_event_id_unique ON outbox (event_id);

CREATE TABLE command_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    aggregate_id UUID NOT NULL,
    response_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Make Retries Idempotent

Commands, event handlers, webhooks, outbox relays, and external calls should not double-apply money, inventory, lifecycle transitions, or notifications when retried.

Use idempotency keys, dedupe records, unique constraints, event IDs, or exactly-once processing guarantees from the infrastructure where available. The repository or handler protocol should show where the idempotency key enters.

```python
async def save_en_route(..., idempotency_key: str) -> None:
    async with conn.transaction():
        existing = await conn.fetchrow(
            "SELECT response_hash FROM command_idempotency WHERE idempotency_key = $1",
            idempotency_key,
        )
        if existing is not None:
            return  # prior attempt succeeded; return cached response if needed

        await _do_save(...)
        await conn.execute(
            "INSERT INTO command_idempotency (idempotency_key, aggregate_id) VALUES ($1, $2)",
            idempotency_key,
            state.request_id,
        )
```

## Version Persisted Events

Events are long-lived contracts. Include event name/type, version, event ID, occurred timestamp, aggregate ID, and payload with explicit units and precision.

```python
class DriverAssigned(DomainModel):
    event_name: Literal["driver_assigned"] = "driver_assigned"
    event_version: Literal[1] = 1
    event_id: UUID
    event_at: datetime
    aggregate_id: UUID
    driver_id: UUID
    passenger_id: UUID
```

When stored or consumed asynchronously, define a backward-compatible deserialization plan before changing event payloads.

## Event Schema Evolution

**Checklist mapping (12.6):** Every stored event needs `event_name` + `event_version` and a documented migration path.

### Versioning rules

| Change | Strategy | Consumer action |
| --- | --- | --- |
| Add optional field | Bump `event_version`; new field has default or `None` | Old consumers ignore unknown fields if they parse through a versioned DTO with `extra="ignore"` |
| Add required field | New `event_version` only; never retrofit old rows | Consumers branch on `event_version` or use upcaster |
| Rename field | New version; upcaster maps v1 → v2 on read | Replay jobs run upcaster before domain handler |
| Remove field | Stop emitting; keep deserializing old versions | Tombstone documentation in event catalog |
| Change semantic (units, enum) | New `event_name` or version; do not overload meaning | Explicit breaking-change note |

### Upcaster on consume

```python
DriverAssignedAdapter = TypeAdapter(DriverAssigned)


def parse_driver_assigned(raw: dict[str, object]) -> DriverAssigned:
    version = raw.get("event_version", 1)
    if version == 1:
        return DriverAssignedAdapter.validate_python(raw)
    if version == 2:
        dto = DriverAssignedV2Adapter.validate_python(raw)
        return DriverAssigned(
            event_id=dto.event_id,
            event_at=dto.event_at,
            aggregate_id=dto.aggregate_id,
            driver_id=dto.driver_id,
            passenger_id=dto.passenger_id,
        )
    raise UnsupportedEventVersion(event_name="driver_assigned", version=version)
```

### Dual-write / dual-read window

When migrating live traffic:

1. Deploy consumers that accept **both** v1 and v2.
2. Deploy producers that emit v2 (or both during transition).
3. Backfill historical outbox/archive rows with an offline job if needed.
4. Remove v1 support only after metrics show zero v1 traffic.

Keep event payloads aligned with [`pii-protection.md`](./pii-protection.md): new fields that carry PII need retention and redaction review.
