# Domain Modeling

## Use Pydantic v2 Variants for Domain States

Assume Python 3.13.14 and Pydantic v2. Define each business state as a separate frozen Pydantic model. Use one project-wide discriminator named `kind`.

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

When stronger nominal separation is required, wrap the value in a frozen model rather than relying only on type aliases.

Domain constructors and Pydantic adapters should be authoritative. Tests, repositories, native adapters, and migrations should not construct invariant-bearing values through raw dicts or `model_construct` unless the purpose is explicitly corrupted-data handling.

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

For new repositories, create a uv-managed project with Python 3.13.14 and Pydantic v2.

```bash
uv init --package
uv python pin 3.13.14
uv add "pydantic>=2,<3"
uv lock
```

For skill or documentation repositories that are not importable Python packages, set `package = false` under `[tool.uv]`.

## Configure Mypy With the Pydantic Plugin

Use the Pydantic v2 mypy plugin in projects that rely on Pydantic domain models. It improves static checks for model `__init__`, `model_construct`, frozen models, field defaults, untyped fields, and dynamic aliases.

```toml
[tool.mypy]
python_version = "3.13"
strict = true
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

Keep `init_typed = true` so constructor calls are checked against field types instead of accepting `Any` for Pydantic's default coercion behavior. Keep `init_forbid_extra = true` so unexpected constructor keywords are not hidden behind `**kwargs: Any`. Avoid required dynamic aliases on domain models because they weaken constructor checking.
