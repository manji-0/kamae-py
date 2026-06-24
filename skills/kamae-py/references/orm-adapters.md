# ORM Adapters and Domain Mappers

> **When to read:** Mapping SQLAlchemy 2.0 or Django ORM entities to Pydantic domain models in repository adapters.
> **Related:** [`boundary-defense.md`](./boundary-defense.md), [`persistence-events.md`](./persistence-events.md), [`migration-strategy.md`](./migration-strategy.md).


Kamae Python keeps ORM entity classes in **infrastructure**. Use cases and transitions see only Pydantic domain states. Adapters own the translation between persistence rows/entities and domain models.

## Layering

```text
Use case  →  RequestStore (Protocol)  →  SqlAlchemyRequestStore (adapter)
                                              ↓
                                         ORM Entity / row DTO
                                              ↓
                                         mapper functions
                                              ↓
                                         Waiting | EnRoute | ...
```

Never pass SQLAlchemy `Mapped` classes or Django `Model` instances into use cases. They carry lazy loading, session attachment, and nullable columns that weaken domain invariants.

## SQLAlchemy 2.0 Pattern

Define ORM entities separately from domain states. Use `mapped_column` with explicit types; keep the table model persistence-focused.

```python
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RequestRow(Base):
    __tablename__ = "requests"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    passenger_id: Mapped[UUID] = mapped_column(nullable=False)
    driver_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
```

### Row DTO + domain mapper

Parse through a narrow row DTO at the adapter boundary, then map to the discriminated union.

```python
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class RequestRowDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    kind: str
    passenger_id: UUID
    driver_id: UUID | None
    created_at: datetime
    assigned_at: datetime | None


RequestRowDtoAdapter = TypeAdapter(RequestRowDto)


def row_dto_from_orm(row: RequestRow) -> RequestRowDto:
    return RequestRowDtoAdapter.validate_python(
        {
            "id": row.id,
            "kind": row.kind,
            "passenger_id": row.passenger_id,
            "driver_id": row.driver_id,
            "created_at": row.created_at,
            "assigned_at": row.assigned_at,
        }
    )


def domain_from_row_dto(dto: RequestRowDto) -> TaxiRequest:
    match dto.kind:
        case "waiting":
            return Waiting.model_construct(
                kind="waiting",
                request_id=dto.id,
                passenger_id=dto.passenger_id,
                created_at=dto.created_at,
            )
        case "en_route":
            if dto.driver_id is None or dto.assigned_at is None:
                raise CorruptRowError(dto.id, "en_route missing driver or assigned_at")
            return EnRoute.model_construct(
                kind="en_route",
                request_id=dto.id,
                passenger_id=dto.passenger_id,
                driver_id=dto.driver_id,
                assigned_at=dto.assigned_at,
            )
        case other:
            raise CorruptRowError(dto.id, f"unknown kind {other!r}")
```

`model_construct` is acceptable here because `RequestRowDto` already validated types and the `match` enforces per-`kind` field presence. Add tests for every `kind` and corrupt-row cases.

### Persisting domain → ORM

```python
def orm_fields_from_en_route(state: EnRoute, *, version: int) -> dict[str, object]:
    return {
        "id": state.request_id,
        "kind": state.kind,
        "passenger_id": state.passenger_id,
        "driver_id": state.driver_id,
        "created_at": state.assigned_at,  # or carry created_at on all states
        "assigned_at": state.assigned_at,
        "version": version,
    }


class SqlAlchemyRequestStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_en_route(
        self,
        state: EnRoute,
        events: tuple[DriverAssigned, ...],
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> None:
        row = await self._session.get(RequestRow, state.request_id, with_for_update=True)
        if row is None or row.version != expected_version:
            raise VersionConflict(state.request_id)
        for key, value in orm_fields_from_en_route(state, version=expected_version + 1).items():
            setattr(row, key, value)
        for event in events:
            self._session.add(outbox_from_event(event, idempotency_key=idempotency_key))
```

Keep optimistic locking and outbox inserts in the adapter; the use case passes `expected_version` and `idempotency_key` explicitly. Read [`persistence-events.md`](./persistence-events.md).

## Django ORM Pattern

Django models stay in `infrastructure` or `models.py` at the app edge—not in domain packages.

```python
# infrastructure/request_mapper.py
from myapp.models import Request as RequestModel


def row_dto_from_django(instance: RequestModel) -> RequestRowDto:
    return RequestRowDtoAdapter.validate_python(
        {
            "id": instance.id,
            "kind": instance.kind,
            "passenger_id": instance.passenger_id,
            "driver_id": instance.driver_id,
            "created_at": instance.created_at,
            "assigned_at": instance.assigned_at,
        }
    )


def domain_from_django(instance: RequestModel) -> TaxiRequest:
    return domain_from_row_dto(row_dto_from_django(instance))
```

For writes, update fields from `model_dump(mode="python")` or explicit field maps inside `transaction.atomic()`:

```python
from django.db import transaction


@transaction.atomic
def save_en_route_django(
    state: EnRoute,
    events: tuple[DriverAssigned, ...],
    *,
    expected_version: int,
) -> None:
    row = RequestModel.objects.select_for_update().get(pk=state.request_id)
    if row.version != expected_version:
        raise VersionConflict(state.request_id)
    row.kind = state.kind
    row.driver_id = state.driver_id
    row.assigned_at = state.assigned_at
    row.version = expected_version + 1
    row.save(update_fields=["kind", "driver_id", "assigned_at", "version"])
    insert_outbox_events(events)
```

## Repository Port Shape

Ports return domain states, not ORM instances. Use the **canonical** port definitions in [`persistence-events.md`](./persistence-events.md#keep-repository-protocols-small). Narrow methods (`find_waiting`, `save_en_route`) document which lifecycle states are valid at each persistence operation.

## Migration Coexistence

During a strangler migration, legacy services may still read dicts or ORM objects. Introduce mappers **before** rewriting business rules:

1. Add `RequestRowDto` + `domain_from_row_dto`.
2. Wrap legacy `TaxiRequestService` methods to call mappers, then pure transitions.
3. Move queries into `SqlAlchemyRequestStore` / Django adapter modules.
4. Delete legacy wrappers when use cases own the flow.

Read [`migration-strategy.md`](./migration-strategy.md) for phased rollout.

## Tests

- **Mapper tests:** every `kind`, null combinations, corrupt rows, timezone-aware datetimes.
- **Adapter integration tests:** real DB transaction, `select_for_update`, version conflict, outbox row in same transaction.
- **Use case tests:** fake ports; no ORM.

Do not construct domain states with raw dicts in mapper tests unless the test targets corrupt input handling.
