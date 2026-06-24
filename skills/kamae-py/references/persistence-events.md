# Persistence and Events

> **When to read:** Designing repositories, transactions, outbox records, idempotent commands, optimistic locking, or event payloads.
> **Related:** [`aggregates.md`](./aggregates.md), [`orm-adapters.md`](./orm-adapters.md), [`infrastructure-resilience.md`](./infrastructure-resilience.md).


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

## Persist State and Events Atomically

When a transition emits domain events, write the aggregate state and outbox/event rows in the same transaction. Avoid APIs that let callers save state and events separately.

```python
async with transaction:
    await update_request_state(state, expected_version=expected_version)
    await insert_outbox_events(events)
```

The outbox worker can publish events after commit. Publishing directly inside the transaction or before the state commit risks duplicate or missing notifications.

## Mirror Critical Invariants in the Database

Use database constraints for invariants the database can enforce: uniqueness, tenant ownership foreign keys, non-negative balances, valid lifecycle states, idempotency keys, and event uniqueness.

Application checks are still needed for good errors and domain clarity, but they are not enough under concurrency.

## Make Retries Idempotent

Commands, event handlers, webhooks, outbox relays, and external calls should not double-apply money, inventory, lifecycle transitions, or notifications when retried.

Use idempotency keys, dedupe records, unique constraints, event IDs, or exactly-once processing guarantees from the infrastructure where available. The repository or handler protocol should show where the idempotency key enters.

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
