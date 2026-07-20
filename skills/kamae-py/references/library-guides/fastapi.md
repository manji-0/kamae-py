# fastapi

For full patterns, prefer [`../application-wiring.md`](../application-wiring.md), [`../boundary-defense.md`](../boundary-defense.md), and [`../error-handling.md`](../error-handling.md).
This file covers library-specific defaults only.

Keep FastAPI at the **interface** layer. Routes parse transport DTOs, call use cases, and map `Result` / domain errors to HTTP responses. Domain packages must not import `fastapi`.

## Route → Use Case Shape

```python
from fastapi import APIRouter, Depends, Response, status


router = APIRouter()


@router.post("/requests/{request_id}/assign-driver", status_code=status.HTTP_204_NO_CONTENT)
async def assign_driver(
    request_id: UUID,
    body: AssignDriverBody,
    use_case: AssignDriverUseCase = Depends(get_assign_driver_use_case),
    actor: Actor = Depends(get_actor),
    clock: Clock = Depends(get_clock),
) -> Response:
    result = await use_case(
        actor=actor,
        request_id=request_id,
        driver_id=body.driver_id,
        now=clock.now(),
    )
    if result.is_err():
        raise http_error_for(result.error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- Use `Depends` only at the controller / composition root to build ports — not inside pure transitions.
- Prefer explicit response DTOs when returning state; do not dump domain models that may contain PII.

## Validation and Errors

- Let FastAPI raise `RequestValidationError` for request-body shape failures; map Pydantic `ValidationError` from deeper adapters to 422 with redacted details — see [`../boundary-defense.md`](../boundary-defense.md#http-mapping).
- Map expected domain failures to stable status codes (`404`, `409`, `403`) via use-case-specific error unions — see [`../error-handling.md`](../error-handling.md#convert-errors-at-the-controller-boundary).

## Lifespan and Workers

Wire process pools, DB pools, and OpenTelemetry exporters in FastAPI lifespan (or an equivalent app factory). Do not create global clients at import time inside domain modules. Pair with [`../concurrency.md`](../concurrency.md) and [`../service-boundaries.md`](../service-boundaries.md) when calling outbound HTTP.

## Common Combinations

| Stack | Pattern | Topic guide |
| --- | --- | --- |
| FastAPI + Pydantic v2 | Body DTO → command | [`./pydantic.md`](./pydantic.md) |
| FastAPI + SQLAlchemy | Session in adapter, not domain | [`./sqlalchemy.md`](./sqlalchemy.md) |
| FastAPI + OTel | Spans around use cases | [`../logging-metrics.md`](../logging-metrics.md) |
