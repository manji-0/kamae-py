# sqlalchemy

For full patterns, prefer [`../orm-adapters.md`](../orm-adapters.md), [`../persistence-events.md`](../persistence-events.md), and [`../boundary-defense.md`](../boundary-defense.md).
This file covers library-specific defaults only.

Use **SQLAlchemy 2.0** style (`select()`, `mapped_column`, `AsyncSession`) when the project already depends on SQLAlchemy. Keep ORM entities in infrastructure; map to frozen Pydantic domain states at the adapter edge.

## Layering

```text
ORM entity / Row  --mapper-->  Pydantic domain state
Session / transaction         --implements-->  RequestStore Protocol
```

Domain and application modules depend on `typing.Protocol` ports only. They must not import `sqlalchemy` or hold `Session` / `AsyncSession` references.

## Mapper Defaults

- Prefer explicit `to_domain(row) -> TaxiRequest` and `to_row(state) -> Entity` helpers.
- Rehydrate through `TypeAdapter` (or constructors) so discriminators and invariants run.
- Reserve `model_construct` for trusted, already-validated DB values inside the mapper — document why — see [`../unsafe-boundaries.md`](../unsafe-boundaries.md#model_construct-in-orm-mappers).

## Transactions

Begin/commit in the use-case-owned adapter method (or a unit-of-work port), not in domain transitions. Persist aggregate state and outbox rows in the same transaction — [`../persistence-events.md`](../persistence-events.md#persist-state-and-events-atomically).

```python
async def save(
    self,
    state: TaxiRequest,
    events: list[DomainEvent],
    *,
    expected_version: int,
) -> None:
    async with self._session.begin():
        await self._update_state(state, expected_version=expected_version)
        await self._insert_outbox(events)
```

## Common Combinations

| Stack | Pattern | Topic guide |
| --- | --- | --- |
| SQLAlchemy + Pydantic | Mapped rows ↔ discriminated states | [`../orm-adapters.md`](../orm-adapters.md) |
| SQLAlchemy + optimistic lock | `version` column + conflict error | [`../persistence-events.md`](../persistence-events.md#optimistic-locking) |
| Django ORM instead | Same port/mapper stance | [`../orm-adapters.md`](../orm-adapters.md#django-orm-pattern) |
