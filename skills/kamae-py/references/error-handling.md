# Error Handling

## Keep Expected Failures Explicit

Use-case failures should be specific to the operation. Avoid one catch-all `AppError` for every business path.

```python
class RequestNotFound(DomainModel):
    kind: Literal["request_not_found"] = "request_not_found"
    request_id: UUID


class InvalidState(DomainModel):
    kind: Literal["invalid_state"] = "invalid_state"
    current_kind: str
    expected_kind: str


type AssignDriverError = Annotated[
    RequestNotFound | InvalidState | DriverNotAvailable,
    Field(discriminator="kind"),
]
```

Use Pydantic error variants when errors cross process, API, queue, or persistence boundaries. Frozen dataclasses are fine for purely in-process errors if the project already prefers them.

## Prefer Result Values for Domain Flow

If the project already uses a Result library, return `Result[Success, Error]` from use cases with expected business failures. Common options include:

- `returns` from dry-python (`Success` / `Failure`)
- `result` from rustedpy (`Ok` / `Err`; check maintenance status before adopting)
- a small local `Ok` / `Err` type

The examples below use `Ok` / `Err`. Adapt constructor and pattern-matching names to the library already in the project.

If the project uses exceptions for application services, keep domain exception classes specific and convert them at the controller boundary. Do not raise broad `Exception`, `ValueError`, or HTTP framework exceptions from domain functions.

Map repository, SDK, and adapter errors into use-case errors at the infrastructure/application boundary. Do not expose low-level driver exception types as the public contract of a domain use case unless the project has explicitly chosen that convention.

Avoid putting raw PII, secrets, access tokens, SQL snippets with customer data, or external payloads into error variants or exception messages.

## Convert Errors at the Controller Boundary

Map domain errors to HTTP or RPC responses outside the domain layer.

```python
def assign_driver_response(result: Result[EnRoute, AssignDriverError]) -> JSONResponse:
    match result:
        case Ok(value=en_route):
            return JSONResponse(en_route.model_dump(mode="json"), status_code=200)
        case Err(error=RequestNotFound()):
            return JSONResponse({"code": error.kind}, status_code=404)
        case Err(error=InvalidState()):
            return JSONResponse({"code": error.kind}, status_code=409)
        case Err(error=DriverNotAvailable()):
            return JSONResponse({"code": error.kind}, status_code=422)
        case _:
            assert_never(result)
```

Adapt the pattern to the project's actual Result shape. If pattern matching is awkward for the chosen library, branch on the library's `is_ok` / `is_err` API and then on `error.kind`.

## Where Exceptions Belong

Exceptions are appropriate for:

- Pydantic `ValidationError` at external boundaries.
- Unexpected infrastructure failures that should be handled by the framework or retry mechanism.
- Programmer errors such as an unreachable `assert_never` path.

Exceptions are not appropriate for normal business outcomes such as "request not found", "invalid state", or "driver unavailable" unless the project has explicitly standardized domain-specific exceptions.
