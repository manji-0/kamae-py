# Error Handling

> **When to read:** Modeling use-case failures, mapping errors to HTTP responses, async `Result` flows, or deciding whether to raise exceptions.
> **Related:** [`state-transitions.md`](./state-transitions.md), [`infrastructure-resilience.md`](./infrastructure-resilience.md), [`pii-protection.md`](./pii-protection.md).


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

Use Pydantic error variants when errors cross process, API, queue, or persistence boundaries. Return `Err` with a specific variant (for example `RequestNotFound(request_id=...)`) rather than factory helpers on a union alias unless the project already standardizes on them. Frozen dataclasses are fine for purely in-process errors if the project already prefers them.

## Prefer Result Values for Domain Flow

If the project already uses a Result library, return `Result[Success, Error]` from use cases with expected business failures. Common options include:

- `returns` from dry-python (`Success` / `Failure`)
- `result` from rustedpy (`Ok` / `Err`; check maintenance status before adopting)
- a small local `Ok` / `Err` type

The examples below use `Ok` / `Err`. Adapt constructor and pattern-matching names to the library already in the project.

If the project uses exceptions for application services, keep domain exception classes specific and convert them at the controller boundary. Do not raise broad `Exception`, `ValueError`, or HTTP framework exceptions from domain functions.

Map repository, SDK, and adapter errors into use-case errors at the infrastructure/application boundary. Do not expose low-level driver exception types as the public contract of a domain use case unless the project has explicitly chosen that convention.

Read [`infrastructure-resilience.md`](./infrastructure-resilience.md) for retry, timeout, and circuit-breaker placement in adapters.

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

## Async Use Cases and Result

Server-side use cases are usually `async def` and return `Result[Success, Error]`. In Python this is `Awaitable[Result[T, E]]`; you do not need a separate `ResultAsync` type.

### Separate Business Failures From Infrastructure Failures

| Outcome | Representation | Examples |
| --- | --- | --- |
| Expected business failure | `Err(...)` | not found, invalid state, forbidden |
| Unexpected infrastructure failure | raised exception | DB down, timeout, bug |
| Recoverable concurrency conflict | `Err(...)` when mapped, or retryable exception per project policy | version conflict, duplicate command |

Pure transitions stay synchronous. Only use cases and adapters are async.

### Preferred Pattern: Early Return

Prefer readable early returns over long monadic chains. Start from the **canonical** use case in [`state-transitions.md`](./state-transitions.md#keep-use-cases-thin); add persistence error mapping around `save_en_route`:

```python
    en_route = assign_driver(waiting, driver_id, now)
    event = driver_assigned_event(en_route, now)

    try:
        await store.save_en_route(
            en_route,
            (event,),
            expected_version=waiting.version,
            idempotency_key=str(request_id),
        )
    except VersionConflict:
        return Err(
            InvalidState(
                current_kind=waiting.kind,
                expected_kind="waiting",
            )
        )

    return Ok(en_route)
```

Infrastructure errors that should trigger framework retries or 5xx responses can remain exceptions:

```python
    except InfrastructureError:
        raise
```

Map driver-specific exceptions to use-case errors at the adapter boundary when callers need a stable `Err` contract.

### Library-Specific Async Result Types

If the project already uses `returns`, `FutureResult` / `IOResult` are acceptable. Do not introduce them only for migration aesthetics.

For `result` (`Ok` / `Err`), keep async composition in the use case with early returns. The examples in this reference use `Ok` / `Err` names.

### Controller Boundary Stays Sync-Friendly

Controllers await the use case, then map the `Result` to HTTP/RPC:

```python
async def assign_driver_endpoint(...) -> JSONResponse:
    result = await assign_driver_use_case(...)
    return assign_driver_response(result)
```

Do not let framework response types leak into domain or application modules.
