# State Transitions

## Express Valid Transitions as Functions

Write a pure function for each allowed transition. The input type should be the allowed source state and the return type should be the target state.

```python
from datetime import datetime
from uuid import UUID


def assign_driver(waiting: Waiting, driver_id: UUID, now: datetime) -> EnRoute:
    return EnRoute(
        request_id=waiting.request_id,
        passenger_id=waiting.passenger_id,
        driver_id=driver_id,
        assigned_at=now,
    )
```

Do not accept the full union when only one state is valid. `assign_driver(request: TaxiRequest, ...)` forces runtime rejection of invalid states that the type signature could have prevented.

Keep aggregate-wide unions at API, repository, serialization, or dispatch boundaries. At those boundaries, immediately delegate into handlers that accept the narrow state type.

## Use Partial Unions for Shared Transitions

When a transition is valid from several states, define a named partial union.

```python
type CancellableRequest = Waiting | EnRoute | InTrip


def cancel(request: CancellableRequest, reason: str, now: datetime) -> Cancelled:
    return Cancelled(
        request_id=request.request_id,
        passenger_id=request.passenger_id,
        cancelled_at=now,
        reason=reason,
    )
```

## Inject Time, IDs, Randomness, and Side Effects

Transition functions should not call `datetime.now()`, `uuid4()`, database clients, message brokers, or logging directly. Pass these values in from the use case so tests can pin behavior.

When a transition emits events, prefer returning a small outcome value instead of hiding events in mutable state.

```python
class TransitionOutcome[TState, TEvent](DomainModel):
    state: TState
    events: tuple[TEvent, ...]
```

## Keep Use Cases Thin

Use cases orchestrate loading, checking preconditions, calling pure transitions, building events, and persisting state plus events. Keep business rules in named functions that are easy to unit test.

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
        return Err(RequestNotFound(request_id=request_id))

    en_route = assign_driver(waiting, driver_id, now)
    event = driver_assigned_event(en_route, now)
    await store.save_en_route(en_route, (event,))
    return Ok(en_route)
```

Adapt `Ok` / `Err` names to the result library already used by the project. If the project uses exceptions for application services, keep expected domain failures specific and convert them at the controller boundary.

## Authorize Before Transitioning

Use cases should prove actor, tenant, account, or capability authorization before applying a state transition. The transition function may still accept an authorization value if the permission is part of the domain rule, but do not mutate lifecycle state first and check authorization afterward.

```python
async def assign_driver_use_case(
    resolver: RequestResolver,
    store: RequestStore,
    authorizer: RequestAuthorizer,
    actor: Actor,
    request_id: UUID,
    driver_id: UUID,
    now: datetime,
) -> Result[EnRoute, AssignDriverError]:
    allowed = await authorizer.can_assign_driver(actor, request_id)
    if not allowed:
        return Err(Forbidden(request_id=request_id))
    ...
```

## Protect Concurrent Transitions

Lifecycle and balance transitions need concurrency protection when two commands can race. Use optimistic version fields, conditional updates, unique constraints, idempotency keys, row locks, serializable transactions, or a single-writer queue according to the system's architecture.

Repository protocols should make the concurrency expectation visible.

```python
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

## Model Domain Events as Immutable Records

Create event models beside the aggregate or use case that emits them. Include the aggregate identity and timestamp. Persist state and events in one transaction.

```python
class DriverAssigned(DomainModel):
    event_name: Literal["driver_assigned"] = "driver_assigned"
    event_id: UUID
    event_at: datetime
    aggregate_id: UUID
    driver_id: UUID
    passenger_id: UUID
```

The repository should not invent domain events internally. The use case decides which event happened and passes it to the store with the new state.

## Check Exhaustiveness

Use `typing.assert_never` when branching over a discriminated union. Python 3.13.14 has it in the standard library. Run pyright or mypy in strict enough mode for this to matter.

```python
from typing import assert_never


def describe(request: TaxiRequest) -> str:
    match request:
        case Waiting():
            return "waiting"
        case EnRoute():
            return "en route"
        case InTrip():
            return "in trip"
        case Completed():
            return "completed"
        case Cancelled():
            return "cancelled"
        case _:
            assert_never(request)
```

If the type checker cannot narrow the Pydantic union in the project's version, branch on `request.kind` and keep the `assert_never` fallback.
