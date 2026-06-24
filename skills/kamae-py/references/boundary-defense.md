# Boundary Defense

> **When to read:** Accepting API payloads, DB rows, env vars, files, queue messages, or external SDK responses.
> **Related:** [`unsafe-boundaries.md`](./unsafe-boundaries.md), [`pydantic-performance.md`](./pydantic-performance.md), [`orm-adapters.md`](./orm-adapters.md), [`error-handling.md`](./error-handling.md).


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

```python
def parse_queue_message(body: bytes) -> TaxiRequestEvent:
    return TaxiRequestEventAdapter.validate_json(body)
```

Prefer `model_validate_json` / `TypeAdapter.validate_json` over `json.loads` followed by `validate_python` on hot paths. JSON parsing and schema validation can share work in Pydantic's Rust core. Read [`pydantic-performance.md`](./pydantic-performance.md#validate-python-vs-validate-json) for when the difference matters.

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

## External DTO Configuration

<!-- constrained-by ./domain-modeling.md -->

Domain states use `extra="forbid"` and `frozen=True`. **Inbound DTOs** at external boundaries need a separate configuration profile.

### `strict=True` on external DTOs

Enable strict parsing on wire-facing DTOs so coercion does not hide data quality problems (`"123"` → `123`, `"true"` → `True`).

```python
from pydantic import BaseModel, ConfigDict, Field


class CreateRequestInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    passenger_id: UUID
    pickup_lat: float = Field(ge=-90, le=90)
    pickup_lng: float = Field(ge=-180, le=180)
```

Use `strict=True` when:

- The payload comes from HTTP, queues, webhooks, or third-party SDKs.
- Silent coercion would change business meaning (amounts, booleans, enums).
- You want validation failures to surface upstream data bugs early.

Do **not** apply `strict=True` to internal handoffs where both sides are Python code and types already match. That adds cost without safety gain. Read [`pydantic-performance.md`](./pydantic-performance.md#reduce-work-without-bypassing-invariants).

`ConfigDict(strict=True)` is equivalent to marking every field with `Strict*` types (`StrictInt`, `StrictStr`, …). Prefer the model-level flag on DTOs; use per-field strict types only when one field needs coercion and the rest do not.

### `extra="allow"` vs `extra="forbid"` decision table

| Model role | `extra` | `strict` | Rationale |
| --- | --- | --- | --- |
| Domain state / event | `forbid` | default | Invalid fields must not enter persistence or logs |
| Inbound HTTP/command DTO | `forbid` | `True` | Reject unknown or misspelled keys before domain conversion |
| Outbound response DTO | `forbid` | default | Prevent accidental field leakage |
| Webhook / partner feed (version-tolerant ingest) | `allow` | `True` | Accept forward-compatible vendor fields; map known subset to domain |
| ORM row / DB projection DTO | `forbid` | default | Column set is fixed; extra keys indicate mapper bugs |
| Config / feature-flag snapshot | `ignore` | default | Unknown keys from older deploys can be dropped safely |
| Audit / debug capture (non-domain) | `allow` | default | Store raw envelope separately; never pass through to transitions |

**Checklist mapping (4.3, 4.4):** Flag `extra="allow"` on domain states. Flag broad defaults on inbound DTOs when a missing field would silently change behavior. Prefer explicit required fields and `extra="forbid"` unless you document a compatibility reason.

When `extra="allow"` is required, keep the DTO in the adapter layer and map only declared fields into domain constructors. Do not subclass or inherit permissive DTOs into domain models.

### DTO defaults and unknown fields

Avoid defaults that change business meaning when the client omits a field:

```python
# Risky: omitted "currency" silently becomes USD.
class ChargeInput(BaseModel):
    amount_cents: int
    currency: str = "USD"


# Prefer: require explicit values at the boundary.
class ChargeInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    amount_cents: int = Field(gt=0)
    currency: Literal["USD", "EUR", "JPY"]
```

For optional fields, use `None` only when "not provided" is a distinct, documented semantic—not when it means "use a hidden default."

## Environment and CLI Boundaries

Use [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) for environment variables and CLI-derived configuration. Treat settings models as DTOs: validated once at process startup, never mixed into domain states.

```bash
uv add pydantic-settings
```

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        strict=True,
    )

    host: str
    port: int = 5432
    name: str
    user: str
    password: SecretStr


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="forbid")

    database: DatabaseSettings
    tenant_header: str = "X-Tenant-Id"
```

Boundaries to respect:

- **Parse at startup** in the composition root (`application-wiring.md`). Do not read `os.environ` inside use cases or transitions.
- **`extra="forbid"`** catches typos in env var names mapped to fields.
- **`SecretStr`** for credentials; never log settings with `model_dump()`.
- **CLI flags** can populate a settings model via `CliSettingsSource` or a thin argparse layer that builds a Pydantic model—same validation rules as env-based config.
- **Per-request values** (tenant ID, actor ID) are not settings. They belong in request context, not `BaseSettings`. See [`application-wiring.md`](./application-wiring.md).

## Authorization and Tenant Boundaries

<!-- constrained-by ./error-handling.md -->

**Checklist mapping (4.6):** Never trust tenant or actor IDs from path, query, body, or message payload without comparing them to authenticated context.

### API gateway injection pattern

A common layout:

```text
Client → API gateway (authn) → service (authz + domain)
         injects: tenant_id, subject, scopes
```

The gateway validates the session or token and forwards trusted headers. The service still validates that the operation is allowed for that tenant.

```python
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RequestContext:
    tenant_id: UUID
    actor_id: UUID
    scopes: frozenset[str]


class AssignDriverBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    driver_id: UUID
    # Do NOT accept tenant_id from body when gateway already established tenant.


async def assign_driver_endpoint(
    body: AssignDriverBody,
    ctx: RequestContext,  # from middleware / dependency
    request_id: UUID,  # from path
) -> JSONResponse:
    result = await assign_driver_use_case(
        ctx=ctx,
        request_id=request_id,
        driver_id=body.driver_id,
    )
    return assign_driver_response(result)
```

### Domain-layer verification

Authorization belongs in the **use case**, after load, before transition:

```python
async def assign_driver_use_case(
    ctx: RequestContext,
    request_id: UUID,
    driver_id: UUID,
    *,
    store: RequestStore,
    resolver: RequestResolver,
) -> Result[EnRoute, AssignDriverError]:
    waiting = await resolver.find_waiting(request_id)
    if waiting is None:
        return Err(RequestNotFound(request_id=request_id))

    # Tenant ownership is a domain/application invariant, not a DTO concern.
    if waiting.tenant_id != ctx.tenant_id:
        return Err(RequestNotFound(request_id=request_id))  # or TenantMismatch

    if "driver:assign" not in ctx.scopes:
        return Err(Forbidden())

    en_route, events = assign_driver(waiting, driver_id, now=utc_now())
    await store.save_en_route(en_route, events, expected_version=waiting.version, ...)
    return Ok(en_route)
```

Rules:

- Compare resource `tenant_id` to `ctx.tenant_id` on every mutating command.
- Prefer `404` or a generic denial for cross-tenant ID probing; document the policy.
- Put `tenant_id` on aggregate state or row DTOs so persistence can enforce FK constraints.
- Queue consumers must rebuild `RequestContext` from signed message metadata, not from unauthenticated payload fields.

## Forbid Extra Fields on Domain State

Use `extra="forbid"` on domain states and event models to avoid silently accepting fields that should not exist. This matters for logging and persistence because extra fields can carry sensitive data through layers that did not intend to handle them.

## Avoid Unchecked Casts

Do not use `typing.cast`, `# type: ignore`, unchecked `dict[str, Any]`, or `model_construct` to turn boundary data into trusted domain objects. These tools bypass validation.

Acceptable narrow exceptions:

- `model_construct` inside a tested mapper that receives values already validated by the database driver or a prior Pydantic parse. Read [`unsafe-boundaries.md`](./unsafe-boundaries.md#model_construct-in-orm-mappers).
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

### HTTP mapping

```python
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def validation_error_response(exc: ValidationError | RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "details": [
                {
                    "loc": list(err["loc"]),
                    "type": err["type"],
                    "msg": err["msg"],
                }
                for err in exc.errors()
            ],
        },
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
    return validation_error_response(exc)
```

Do not return raw Pydantic error dicts to clients without reviewing fields for PII. Strip input values from public responses when they might contain secrets.

### gRPC mapping

```python
import grpc
from pydantic import ValidationError


def validation_error_status(exc: ValidationError) -> grpc.aio.ServicerContext:
    # Return INVALID_ARGUMENT; attach sanitized details in trailing metadata if needed.
    details = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
    return grpc.StatusCode.INVALID_ARGUMENT, details
```

Map to `INVALID_ARGUMENT` for shape violations, not `INTERNAL`.

### Queue / worker mapping

```python
async def handle_message(body: bytes) -> None:
    try:
        event = TaxiRequestEventAdapter.validate_json(body)
    except ValidationError as exc:
        logger.warning("dropping invalid message", extra={"error_count": exc.error_count()})
        await dead_letter.publish(body, reason="validation_error")
        return  # do not retry forever on poison shape

    await process_event(event)
```

Poison messages (permanent validation failure) go to a dead-letter queue. Transient failures use retry with backoff. Read [`persistence-events.md`](./persistence-events.md#outbox-relay-at-least-once-delivery).

### Layer responsibility

| Layer | Catches `ValidationError`? | Returns |
| --- | --- | --- |
| HTTP controller / gRPC servicer | Yes | 422 / `INVALID_ARGUMENT` |
| Queue consumer | Yes | DLQ or metric + drop |
| CLI | Yes | exit code 2 + stderr |
| DTO → domain mapper | Yes (or lets bubble to controller) | domain error or re-raise |
| Pure transition | No | N/A |
| Use case (trusted state) | No | N/A |
