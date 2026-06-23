# Domain Modeling

## Use Pydantic v2 Variants for Domain States

Assume Python 3.12+ and Pydantic v2. Define each business state as a separate frozen Pydantic model. Use one project-wide discriminator named `kind`.

```python
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Waiting(DomainModel):
    kind: Literal["waiting"] = "waiting"
    request_id: UUID
    passenger_id: UUID
    created_at: datetime


class EnRoute(DomainModel):
    kind: Literal["en_route"] = "en_route"
    request_id: UUID
    passenger_id: UUID
    driver_id: UUID
    assigned_at: datetime


class InTrip(DomainModel):
    kind: Literal["in_trip"] = "in_trip"
    request_id: UUID
    passenger_id: UUID
    driver_id: UUID
    started_at: datetime


class Completed(DomainModel):
    kind: Literal["completed"] = "completed"
    request_id: UUID
    passenger_id: UUID
    driver_id: UUID
    started_at: datetime
    completed_at: datetime


class Cancelled(DomainModel):
    kind: Literal["cancelled"] = "cancelled"
    request_id: UUID
    passenger_id: UUID
    cancelled_at: datetime
    reason: str


type TaxiRequest = Annotated[
    Waiting | EnRoute | InTrip | Completed | Cancelled,
    Field(discriminator="kind"),
]

TaxiRequestAdapter = TypeAdapter(TaxiRequest)
```

Prefer lower snake case discriminator values for JSON-facing Python services unless the project already uses another convention.

## Avoid Blob Models With Optional State Fields

Do not model a workflow as one model with `status: str` and many optional fields. Optional fields make invalid states representable.

```python
# Avoid this shape for domain state.
class TaxiRequest(BaseModel):
    status: str
    request_id: UUID
    passenger_id: UUID
    driver_id: UUID | None = None
    assigned_at: datetime | None = None
    completed_at: datetime | None = None
```

If a field exists only in one state, make it required on that state's model.

## Keep State Models Frozen

Set `ConfigDict(frozen=True, extra="forbid")` on domain Pydantic models. State changes should construct a new target state instead of mutating the existing model. Consider `strict=True` at external DTO boundaries when coercion would hide data quality problems.

Avoid public setters, partial update helpers, or `model_copy(update=...)` paths that can violate cross-field invariants. If an update is a business action, name it as a transition or command and make it validate the full invariant.

With the Pydantic mypy plugin enabled, frozen models are also statically checked: assigning to a model field should fail in mypy before runtime.

## Separate Domain Models From Transport DTOs When Needed

It is acceptable for API DTOs and domain models to differ. Use DTOs for endpoint-specific payloads, then map validated DTOs into domain models or command objects. Avoid exposing persistence-only fields or framework concerns on core domain states.

## Use Explicit Value Types for Semantic IDs

Use built-in precise types such as `UUID`, `EmailStr`, `HttpUrl`, constrained strings, or small frozen Pydantic models for values with domain meaning. Do not pass unrelated IDs around as bare `str` when the distinction matters.

```python
from pydantic import StringConstraints
from typing import Annotated

RequestCode = Annotated[str, StringConstraints(pattern=r"^req-[0-9]{8}$")]
```

`Annotated` aliases and `typing.NewType` are **structurally equivalent** to their base type at runtime. Mypy/pyright catch some mistakes, but nothing stops `passenger_id` from being passed where `driver_id` is expected when both are `UUID`. Prefer stronger patterns when ID mix-ups have business impact.

### Prefer Frozen Wrapper Models for Nominal IDs

Wrap each semantic ID in its own frozen Pydantic model (or `@dataclass(frozen=True, slots=True)` for in-process-only IDs). Construction validates format; the wrapper type is not interchangeable with siblings.

```python
from uuid import UUID

from pydantic import field_validator


class PassengerId(DomainModel):
    value: UUID


class DriverId(DomainModel):
    value: UUID


class RequestId(DomainModel):
    value: UUID

    @field_validator("value")
    @classmethod
    def not_nil(cls, value: UUID) -> UUID:
        if value.int == 0:
            raise ValueError("request id must not be nil")
        return value
```

Use distinct parameter names and types in transitions:

```python
def assign_driver(waiting: Waiting, driver_id: DriverId, now: datetime) -> EnRoute:
  ...
```

### `__init_subclass__` Guard for Non-Instantiable Bases

When several ID types share validation logic, use an abstract base that refuses direct instantiation. Subclasses remain distinct nominal types.

```python
class SemanticId(DomainModel):
    value: UUID

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls is SemanticId:
            raise TypeError("SemanticId cannot be instantiated directly")


class TenantId(SemanticId):
    pass


class AccountId(SemanticId):
    pass
```

Add per-subclass validators only where rules differ. Do not use a single generic `Id[T]` wrapper unless the codebase already standardizes on that pattern.

### What Not to Rely On

| Approach | Static check | Runtime separation |
| --- | --- | --- |
| `UUID` parameter names only | Weak | None |
| `Annotated[UUID, ...]` / `NewType` | Good | None |
| Frozen wrapper model per ID | Good | Good (distinct types) |
| `str` with regex constraint | Shape only | No ID-kind separation |

`NewType` remains acceptable for lightweight documentation when runtime mix-ups are harmless. For money, tenant boundaries, or auth-sensitive IDs, use wrapper models.

Domain constructors and Pydantic adapters should be authoritative. Tests, repositories, native adapters, and migrations should not construct invariant-bearing values through raw dicts or `model_construct` unless the purpose is explicitly corrupted-data handling. Read [`pydantic-performance.md`](./pydantic-performance.md) for when `model_construct` is appropriate in trusted mappers.

## Define Repository Ports With Protocols

Use `typing.Protocol` for domain-facing ports. Keep method signatures narrow and return domain states or explicit result types.

```python
from typing import Protocol


class RequestResolver(Protocol):
    async def find_waiting(self, request_id: UUID) -> Waiting | None: ...


class RequestStore(Protocol):
    async def save_en_route(
        self,
        state: EnRoute,
        events: tuple[DomainEvent, ...],
    ) -> None: ...
```

Protocol classes describe ports. They are not domain entities.

Keep API DTOs, DB row models, read models, and domain models separate when an external representation can bypass invariants, includes extra fields, or has different privacy/serialization requirements.

## One Concept Per Module

Prefer modules like `request_id.py`, `taxi_request.py`, and `request_repository.py`. Avoid catch-all files such as `models.py`, `types.py`, or `schemas.py` once they start mixing unrelated concepts.

## Manage the Project With uv

For new repositories, create a uv-managed project with Python 3.12+ and Pydantic v2.

```bash
uv init --package
uv python pin 3.13
uv add "pydantic>=2,<3"
uv lock
```

For skill or documentation repositories that are not importable Python packages, set `package = false` under `[tool.uv]`.

## Configure Mypy With the Pydantic Plugin

Use the Pydantic v2 mypy plugin in projects that rely on Pydantic domain models. It improves static checks for model `__init__`, `model_construct`, frozen models, field defaults, untyped fields, and dynamic aliases.

```toml
[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

Keep `init_typed = true` so constructor calls are checked against field types instead of accepting `Any` for Pydantic's default coercion behavior. Keep `init_forbid_extra = true` so unexpected constructor keywords are not hidden behind `**kwargs: Any`. Avoid required dynamic aliases on domain models because they weaken constructor checking.

## Choose Pydantic, dataclasses, or attrs

Pydantic v2 is the default for Kamae Python domain states, boundary DTOs, and error variants that cross process boundaries. Lighter tools are acceptable when validation and JSON schema are not required.

| Need | Prefer |
| --- | --- |
| Discriminated union states, boundary parsing, JSON/API contracts | **Pydantic v2** frozen models |
| Errors or events crossing HTTP, queue, or persistence | **Pydantic v2** with `kind` discriminator |
| Small in-process value objects with no external serialization | **`@dataclass(frozen=True, slots=True)`** or **attrs frozen** |
| Internal command/outcome tuples used only inside one module | **dataclass** or **NamedTuple** |
| Rich validators, converters, or `attrs` ecosystem plugins | **attrs** with `frozen=True` |

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str
```

Keep money, IDs, and lifecycle states on Pydantic when they appear in logs, APIs, repositories, or events. Use dataclasses/attrs for hot-path helpers that never leave the domain module.

Do not mix representations for the same concept without an explicit mapper at the module boundary.

## Decorators and Explicit Style

Kamae Python favors explicit fields, constructors, and function arguments over hidden behavior. Decorators can coexist when their effect is local and does not replace domain invariants.

| Decorator | Domain / transition code | Boundary / adapter code |
| --- | --- | --- |
| `@property` | Avoid on aggregate states; prefer plain fields | Acceptable for thin adapter views |
| `@cached_property` | Avoid; hides time-dependent or expensive work inside a "value" | Rare; prefer injecting a precomputed value |
| `@validate_call` | Avoid on pure transitions; types should already be narrow | Useful on small parse/convert helpers |
| `@functools.wraps` | Fine for logging or tracing wrappers at infrastructure edges | Fine |

```python
# Prefer explicit fields on domain states.
class Waiting(DomainModel):
    kind: Literal["waiting"] = "waiting"
    request_id: UUID
    ...


# Avoid computed lifecycle state that performs I/O or caching.
class Waiting(DomainModel):
    @cached_property
    def display_label(self) -> str: ...  # hides work; hard to test in isolation
```

Pure transition functions should take every input as a parameter. If a decorator changes observable behavior (validation, caching, I/O), keep it outside the transition and inside an adapter or use case where dependencies are visible in the signature.

`@property` is acceptable on small immutable value objects when it is a pure derivation from existing fields and does not perform I/O:

```python
@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days
```

When Pydantic field validators or `model_validator` replace decorator-heavy classes, prefer validators on frozen models so construction stays the single validation entry point.
