# Test Data

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

## Test Persistence and Retry Behavior

When persistence changes, cover DB constraint failures, optimistic-lock conflicts, transaction rollback, duplicate commands, idempotency keys, outbox insertion, and event version compatibility.

Use fake repositories for pure use-case tests and adapter/integration tests for transaction and constraint behavior.

## Use Property-Based Tests for Stable Invariants

Use Hypothesis or the project's property-test library when an invariant should hold across many inputs: value-object constructors, parser/formatter round trips, state-machine transition laws, money arithmetic, unit conversions, and timestamp boundary rules.

Generated values should still flow through public constructors or Pydantic adapters. A generator that fills private/raw fields can accidentally test states production code cannot construct.
