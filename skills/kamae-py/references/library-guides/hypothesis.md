# hypothesis

For full patterns, prefer [`../test-data.md`](../test-data.md).
This file covers library-specific defaults only.

Add Hypothesis as a **dev** dependency when property tests are the clearest way to cover input-wide invariants:

```bash
uv add --dev hypothesis
```

## Defaults

- Generate values through **public constructors** and Pydantic adapters, not private fields or `model_construct`.
- Prefer explicit `st.builds(...)` for constrained domain models over unrestricted `from_type`.
- Keep custom strategies beside fixtures so example-based and property-based tests share construction helpers.
- One property per invariant so shrinking stays readable.

```python
from hypothesis import given, strategies as st


@given(
    request_id=st.uuids(),
    passenger_id=st.uuids(),
    driver_id=st.uuids(),
    created_at=st.datetimes(timezones=st.just(timezone.utc)),
    assigned_at=st.datetimes(timezones=st.just(timezone.utc)),
)
def test_assign_driver_preserves_identity(...): ...
```

## Good Targets

- Value-object constructors and validation rules
- `TypeAdapter` round trips
- State-transition laws (identity, discriminator, event shape)
- Money / units / timestamp boundaries
- Redaction helpers

Prefer ordinary pytest tables when the case set is small and closed.

## CI Notes

Copy `@reproduce_failure` blobs or seed from CI failure output. Register strategies next to fixtures; do not put generators in production domain packages.

See state-transition laws and round-trip examples in [`../test-data.md`](../test-data.md#use-property-based-tests-for-stable-invariants).
