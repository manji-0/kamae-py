# Boundary Defense

## Parse Unknown Data at the Edge

Treat API bodies, DB rows, queue messages, files, environment variables, and SDK responses as unknown until Pydantic validates them.

```python
CreateRequestInputAdapter = TypeAdapter(CreateRequestInput)


def parse_create_request_input(raw: object) -> CreateRequestInput:
    return CreateRequestInputAdapter.validate_python(raw)
```

For discriminated unions, parse through the union adapter.

```python
request = TaxiRequestAdapter.validate_python(raw_request)
```

Use `validate_json` for raw JSON bytes or strings.

## Prefer DTOs at Framework Boundaries

Framework request models can be DTOs. Convert them into domain command values or domain states after validation. Do not let framework-only concerns leak into domain models.

```python
class AssignDriverBody(BaseModel):
    driver_id: UUID


async def assign_driver_endpoint(body: AssignDriverBody) -> JSONResponse:
    result = await assign_driver_use_case(..., driver_id=body.driver_id, ...)
    return assign_driver_response(result)
```

Pydantic proves shape and declared validators, not all domain meaning. Keep domain constructors, command builders, or transition precondition functions as the authoritative place for business invariants that also apply outside HTTP.

## Forbid Extra Fields on Domain State

Use `extra="forbid"` on domain states and event models to avoid silently accepting fields that should not exist. This matters for logging and persistence because extra fields can carry sensitive data through layers that did not intend to handle them.

## Avoid Unchecked Casts

Do not use `typing.cast`, `# type: ignore`, unchecked `dict[str, Any]`, or `model_construct` to turn boundary data into trusted domain objects. These tools bypass validation.

Acceptable narrow exceptions:

- `model_construct` inside a tested mapper that receives values already validated by the database driver or a prior Pydantic parse.
- `cast` around framework limitations when accompanied by a short comment and a nearby runtime validation step.

Generated clients, native adapters, and ORMs often return values with types that are too broad or too trusted. Convert through DTO/row models first, then into domain models.

## Persist and Rehydrate Through Schemas

When reading from a database, parse rows into domain models before handing them to use cases. When writing to a database, dump models intentionally with `model_dump(mode="python")` or `model_dump(mode="json")` depending on the driver.

```python
def request_from_row(row: Mapping[str, object]) -> TaxiRequest:
    return TaxiRequestAdapter.validate_python(row)


def request_to_row(request: TaxiRequest) -> dict[str, object]:
    return request.model_dump(mode="python")
```

Do not let ORM models become domain models by default. They carry persistence concerns, lazy-loading behavior, nullable columns, and extra fields that can weaken domain invariants.

## Handle Validation Errors Outside the Domain

Pydantic raises `ValidationError`. Catch it in controllers, message consumers, CLI handlers, or mapper layers and convert it to the local error/response shape. Do not make pure transition functions catch validation errors from data they should already trust.
