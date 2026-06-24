# Test Data

> **When to read:** Adding fixtures, factories, property-based tests, transition tests, boundary tests, or persistence retry tests.
> **Related:** [`state-transitions.md`](./state-transitions.md), [`loggable-identifiers.md`](./loggable-identifiers.md), [`logging-metrics.md`](./logging-metrics.md).


## Build Fixtures Through Public Paths

Fixtures should exercise the same Pydantic adapters, constructors, command builders, and transition functions as production code. Avoid raw dicts, `model_construct`, or partial literals unless the test is explicitly about corrupted input or migration compatibility.

```python
def waiting_request(now: datetime) -> Waiting:
    return Waiting(
        request_id=UUID("00000000-0000-0000-0000-000000000001"),
        passenger_id=UUID("00000000-0000-0000-0000-000000000002"),
        created_at=now,
    )
```

If a fixture helper uses a hard-coded value, name the invariant in the helper or assertion message.

## Cover State-Machine Edges

For important workflows, test:

- Successful transitions.
- Rejected transitions or preconditions.
- Authorization and tenant rejection before transition.
- Exhaustive error mapping at the controller boundary.
- Domain events emitted with expected event version and aggregate ID.

## Test Boundaries and Observability

Boundary tests should include unknown fields, malformed DTOs, missing required fields, defaulted fields, bad discriminator values, DB row rehydration, and validation error mapping.

Observability tests should verify redacted logs, safe error messages, safe metrics labels, and response DTO serialization when sensitive data is present.

For identifier policy, assert the tier rules from [`loggable-identifiers.md`](./loggable-identifiers.md):

- Tier A/B values never appear in logs, traces, errors, or metric labels.
- Tier C/D values appear only as structured fields, never inside log message strings.
- Metric exports use Tier E labels only.

## Test Persistence and Retry Behavior

When persistence changes, cover DB constraint failures, optimistic-lock conflicts, transaction rollback, duplicate commands, idempotency keys, outbox insertion, and event version compatibility.

Use fake repositories for pure use-case tests and adapter/integration tests for transaction and constraint behavior.

## Use Property-Based Tests for Stable Invariants

Use [Hypothesis](https://hypothesis.readthedocs.io/) or the project's property-test library when an invariant should hold across many inputs. PBT fits Kamae Python well because transitions are pure functions and invariants are explicit.

```bash
uv add --dev hypothesis
```

Good PBT targets:

- Value-object constructors and validation rules.
- Parser/formatter round trips through `TypeAdapter`.
- State-machine transition laws (see below).
- Money arithmetic, unit conversions, and timestamp boundary rules.
- Redaction helpers and safe serialization.

Generated values should still flow through public constructors or Pydantic adapters. A generator that fills private/raw fields can accidentally test states production code cannot construct.

### State-Transition Laws

For each transition, test properties that should hold for every allowed input:

| Law | Example |
| --- | --- |
| Identity preserved | `result.request_id == source.request_id` |
| Discriminator changes correctly | `assign_driver(waiting, ...).kind == "en_route"` |
| Rejected paths stay unreachable | invalid source states never reach the transition function |
| Event count/shape | `len(outcome.events) == 1` and event aggregate ID matches state |

```python
from datetime import datetime, timezone
from uuid import UUID

from hypothesis import given, strategies as st


@given(
    request_id=st.uuids(),
    passenger_id=st.uuids(),
    driver_id=st.uuids(),
    created_at=st.datetimes(timezones=st.just(timezone.utc)),
    assigned_at=st.datetimes(timezones=st.just(timezone.utc)),
)
def test_assign_driver_preserves_identity(
    request_id: UUID,
    passenger_id: UUID,
    driver_id: UUID,
    created_at: datetime,
    assigned_at: datetime,
) -> None:
    waiting = Waiting(
        request_id=request_id,
        passenger_id=passenger_id,
        created_at=created_at,
    )
    en_route = assign_driver(waiting, driver_id, assigned_at)

    assert en_route.request_id == request_id
    assert en_route.passenger_id == passenger_id
    assert en_route.driver_id == driver_id
    assert en_route.kind == "en_route"
```

Compose multi-step laws with `st.builds` or chained transitions when the workflow has a small state space. Keep each property focused on one invariant so failures are easy to shrink.

### Round-Trip and Adapter Properties

```python
from hypothesis import given, strategies as st


@given(st.builds(Waiting, ...))
def test_taxi_request_round_trip(state: Waiting) -> None:
    payload = state.model_dump(mode="json")
    parsed = TaxiRequestAdapter.validate_python(payload)
    assert parsed == state
```

Use `hypothesis.strategies.from_type` only when the type's constructor is the same path production uses. Prefer explicit `st.builds` for Pydantic models with constrained fields.

### Shrinking and Reproducibility

Hypothesis shrinks failing examples automatically. When a property fails in CI, copy the `@reproduce_failure` blob or run with `hypothesis seed=...` from the failure output.

Register custom strategies beside fixtures so example-based and property-based tests share the same construction helpers.
