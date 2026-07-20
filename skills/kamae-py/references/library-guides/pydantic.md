# pydantic

For full patterns, prefer [`../domain-modeling.md`](../domain-modeling.md), [`../boundary-defense.md`](../boundary-defense.md), and [`../state-transitions.md`](../state-transitions.md).
This file covers library-specific defaults only.

Require **Pydantic v2** (`pydantic>=2,<3`). Prefer **2.11+** when using PEP 695 generics such as `TransitionOutcome[TState, TEvent]`.

## Defaults for Domain States

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal


class Waiting(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["waiting"] = "waiting"
    request_id: UUID
    passenger_id: UUID
    created_at: datetime


TaxiRequest = Annotated[
    Waiting | EnRoute | Completed,
    Field(discriminator="kind"),
]
TaxiRequestAdapter = TypeAdapter(TaxiRequest)
```

- Domain states: `extra="forbid"`, `frozen=True`.
- External DTOs: often `strict=True` on fields or `ConfigDict(strict=True)` — see [`../boundary-defense.md`](../boundary-defense.md#external-dto-configuration).
- Parse unknown data with `TypeAdapter.validate_python` / `validate_json` at boundaries only.

## Avoid

| Anti-pattern | Prefer |
| --- | --- |
| `model_construct` on untrusted input | `TypeAdapter` / `model_validate` |
| Optional status blob on one model | Discriminated `kind` variants |
| Pydantic v1 `class Config` / `.parse_obj` | v2 `model_config` / `model_validate` |
| Domain models that import FastAPI types | Separate transport DTOs |

## Common Combinations

| Stack | Pattern | Topic guide |
| --- | --- | --- |
| `pydantic` + ports | Frozen states, thin use cases | [`../state-transitions.md`](../state-transitions.md) |
| `pydantic` + SQLAlchemy | Row ↔ domain mapper | [`../orm-adapters.md`](../orm-adapters.md), [`./sqlalchemy.md`](./sqlalchemy.md) |
| `pydantic` + FastAPI | Request DTO → command | [`./fastapi.md`](./fastapi.md) |
| Hot path / `msgspec` | Boundary speed, then domain | [`../pydantic-performance.md`](../pydantic-performance.md) |
