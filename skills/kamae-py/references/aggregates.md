# Aggregates and Transaction Boundaries

> **When to read:** Choosing aggregate roots, consistency boundaries, optimistic vs pessimistic locking, or cross-aggregate workflows.
> **Related:** [`persistence-events.md`](./persistence-events.md), [`state-transitions.md`](./state-transitions.md), [`error-handling.md`](./error-handling.md).


## What Counts as an Aggregate Here

In Kamae Python, an **aggregate** is the unit of:

- one discriminated state union (`TaxiRequest = Waiting | EnRoute | ...`)
- pure transition functions that change that union
- domain events emitted by those transitions
- one consistency boundary per command

The **aggregate root** is the identity that owns the state union. In the taxi example, `request_id` identifies the `TaxiRequest` aggregate root.

Do not model every database table as an aggregate. Prefer one root per business invariant you must keep consistent in a single command.

## Inside vs Outside the Boundary

| Inside one aggregate | Outside / separate aggregate |
| --- | --- |
| State variants of the same root | `Passenger`, `Driver`, `Payment`, `Invoice` when they have independent lifecycles |
| Value objects referenced by the root state | Foreign keys used only for lookup, not mutated in the same command |
| Events raised by the root's transitions | Events that describe another root's state change |

If two roots must change together on every command, you likely modeled the boundary too small. Merge them or accept eventual consistency.

```python
# Inside TaxiRequest aggregate
type TaxiRequest = Annotated[
    Waiting | EnRoute | InTrip | Completed | Cancelled,
    Field(discriminator="kind"),
]

# Separate aggregate: do not mutate inside assign_driver_use_case
class DriverAvailability(DomainModel):
    driver_id: UUID
    is_available: bool
```

Cross-aggregate rules belong in application orchestration, sagas, or reactive handlers—not inside a single root's pure transition.

## One Use Case, One Aggregate, One Consistency Boundary

Default rule:

```text
HTTP/queue command
  -> use case (application)
       -> load one aggregate state
       -> authorize
       -> pure transition
       -> build domain events
       -> repository.save(state, events)   # single TX
```

A use case should not update two aggregate roots in one transaction unless the project has an explicit, documented exception. When two roots must stay aligned, prefer:

1. **Domain event + handler** for the second aggregate (eventual consistency)
2. **Process manager / saga** with compensating steps
3. **Single aggregate redesign** when true invariants demand atomicity

## Who Owns the Transaction

The **repository adapter** should own the database transaction for `save(...)`. The use case owns business ordering; the adapter owns commit/rollback.

Document transaction ownership on the port method. Parameters match the **canonical** port in [`persistence-events.md`](./persistence-events.md#keep-repository-protocols-small):

```python
class RequestStore(Protocol):
    async def save_en_route(...) -> None:
        """Persist state and outbox rows atomically.

        Opens the transaction, writes aggregate state, inserts events/outbox
        records, and commits. Raises on infrastructure failure or version conflict.
        """
        ...
```

Avoid splitting `save_state` and `insert_events` into separate public repository methods unless tests use an in-memory fake that still enforces atomic semantics.

Map `VersionConflict` to `Err` in the use case — see [`error-handling.md`](./error-handling.md#preferred-pattern-early-return).

## Optimistic vs Pessimistic Concurrency

| Strategy | Use when | Repository signal |
| --- | --- | --- |
| **Optimistic** (default) | Most lifecycle transitions; conflicts are rare or retryable | `expected_version`, conditional `UPDATE`, unique constraints |
| **Pessimistic** | Inventory, balances, seat holds, strong contention | `SELECT ... FOR UPDATE`, row lock, serializable isolation |

Optimistic locking fits frozen state models well: load version, apply pure transition, save with `expected_version`.

Pessimistic locking belongs in the adapter. Do not leak SQL locking details into pure transition functions.

## Invariants: Application vs Database

Keep both layers:

- **Pure transitions** enforce rules that types and functions express clearly.
- **Database constraints** enforce rules that must survive concurrency (`UNIQUE`, `CHECK`, foreign keys, non-negative amounts).

Application checks produce good `Err` values. Database constraints are the backstop when two commands race.

## Aggregate Size Guidance

Start small. A good aggregate:

- has a clear root ID
- has a small state union
- can be loaded and saved in one repository call
- emits events that describe its own history

Split the aggregate when:

- load/save becomes too heavy
- unrelated lifecycles share one blob model
- different commands need different consistency strategies

Read [`persistence-events.md`](./persistence-events.md) for outbox and idempotency details.
