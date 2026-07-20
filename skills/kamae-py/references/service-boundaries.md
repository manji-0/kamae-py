# Service Boundaries

<!-- constrained-by ./boundary-defense.md -->
<!-- constrained-by ./persistence-events.md -->
<!-- constrained-by ./infrastructure-resilience.md -->

> **When to read:** Integrating other HTTP/gRPC services, queue consumers, protobuf/JSON contracts, or cross-service correlation.
> **Related:** [`boundary-defense.md`](./boundary-defense.md), [`persistence-events.md`](./persistence-events.md), [`stream-continuous-queries.md`](./stream-continuous-queries.md), [`logging-metrics.md`](./logging-metrics.md).

## Treat Remote Services Like Any External Boundary

Microservice and partner APIs are DTO boundaries. Convert wire messages into domain commands or integration events with Pydantic at the adapter edge, the same way HTTP handlers and queue consumers do inside a monolith.

```text
Protobuf / JSON message -> integration DTO (TypeAdapter) -> domain command or event
```

Do not import another service's generated protobuf stubs, OpenAPI client models, or SDK response types into domain packages. Keep generated clients in infrastructure (or a dedicated `*-api` package) and map into domain types at the adapter.

```python
from pydantic import BaseModel, ConfigDict, TypeAdapter


class AssignDriverMessageDto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    request_id: str
    driver_id: str
    idempotency_key: str
    schema_version: int = 1


AssignDriverMessageAdapter = TypeAdapter(AssignDriverMessageDto)


def to_command(dto: AssignDriverMessageDto) -> AssignDriverCommand:
    return AssignDriverCommand(
        request_id=RequestId.parse(dto.request_id),
        driver_id=DriverId.parse(dto.driver_id),
        idempotency_key=IdempotencyKey.parse(dto.idempotency_key),
    )
```

## JSON and Protobuf Schema Evolution

Assume producers and consumers deploy independently. Every persisted or queued message needs an explicit compatibility policy.

| Change | Compatibility | Preferred approach |
| --- | --- | --- |
| Add optional field | Backward compatible | New field with default; consumers ignore unknown fields on integration DTOs when dual-reading |
| Add union / discriminator variant | Forward compatible with care | Bump `schema_version` or event version; old consumers skip or dead-letter unknown variants |
| Rename field | Breaking on the wire | Add new field and deprecate old; dual-read during migration |
| Change field type | Breaking | New message type or new `schema_version` on the envelope |
| Remove field | Breaking after deprecation | Dual-read, then remove after all producers stop writing it |

Wrap payloads in a versioned envelope when events cross service boundaries:

```python
class IntegrationEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_type: str
    schema_version: int
    correlation_id: str | None = None
    payload: dict[str, object]
```

Consumers should:

1. Route on `event_type` and `schema_version`.
2. Deserialize into a version-specific DTO with `TypeAdapter`.
3. Convert DTO → domain integration event through validated constructors.
4. Dead-letter or metric-count unknown versions instead of raising unhandled exceptions.

For domain-event versioning inside one service, prefer [`persistence-events.md`](./persistence-events.md#version-persisted-events).

## Message Queues and Async Integration

Queue consumers inherit at-least-once delivery. Handlers must be idempotent and must not assume ordering across partitions unless the broker contract guarantees it.

```python
async def handle_delivery(
    body: bytes,
    *,
    processed: ProcessedCommandStore,
    use_case: AssignDriverUseCase,
) -> None:
    dto = AssignDriverMessageAdapter.validate_json(body)
    command = to_command(dto)
    if await processed.exists(command.idempotency_key):
        return
    result = await use_case.execute(command)
    if result.is_err():
        raise HandlerError.from_domain(result.error)
    await processed.record(command.idempotency_key)
```

Persist idempotency keys in the same store as side effects when possible. Align with [`persistence-events.md`](./persistence-events.md#make-retries-idempotent) for outbox publication and consumer dedupe.

Poison shapes (permanent `ValidationError`) go to a dead-letter queue. Transient infrastructure failures use retry with backoff — see [`boundary-defense.md`](./boundary-defense.md#queue--worker-mapping).

## Resilience at the Adapter Layer

Circuit breakers, timeouts, retries, and rate limits belong in infrastructure adapters — not in domain transitions or use-case business rules.

| Control | Where | Domain impact |
| --- | --- | --- |
| Timeout | `httpx` / gRPC client builder | Map to typed `BillingError.timeout` |
| Retry with backoff | adapter calling external API | Retry only idempotent reads or explicitly keyed writes |
| Circuit breaker | client middleware | Surface `BillingError.unavailable` to the use case |
| Rate limit | gateway or outbound client | Map to `BillingError.rate_limited`; do not spin in domain code |

```python
async def charge(self, request: ChargeRequest) -> Result[ChargeReceipt, AssignDriverError]:
    try:
        response = await self._client.post("/charges", json=request.to_dto())
    except httpx.TimeoutException:
        return Err(AssignDriverError.billing_timeout)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            return Err(AssignDriverError.billing_rate_limited)
        if exc.response.status_code >= 500:
            return Err(AssignDriverError.billing_unavailable)
        return Err(AssignDriverError.billing_rejected)

    receipt = ChargeReceiptAdapter.validate_python(response.json())
    return Ok(receipt)
```

Use cases decide whether a failure is retryable or compensating; adapters execute the policy. Pair with [`infrastructure-resilience.md`](./infrastructure-resilience.md).

## Correlation Across Services

Propagate `correlation_id`, OpenTelemetry `trace_id` / span context, and tenant context on outbound calls and queue messages. Set them on spans at the ingress adapter and inject into headers or message attributes.

Do not treat distributed traces as domain audit logs. Persist business events through the outbox when durability is required — see [`logging-metrics.md`](./logging-metrics.md) and [`loggable-identifiers.md`](./loggable-identifiers.md).

## Contract Testing

When two services share protobuf or JSON schemas:

- Regenerate OpenAPI / protobuf clients in CI or pin checked-in stubs with a refresh job.
- Run consumer-driven contract tests or breaking-change detection before release.
- Keep fixture messages for each supported `schema_version` in tests.

## Detection Hints

When `pyproject.toml` includes `grpcio`, `protobuf`, `httpx`, `aiohttp`, `celery`, `kombu`, `aiokafka`, `redis`, or similar clients, load this guide together with [`boundary-defense.md`](./boundary-defense.md) and [`stream-continuous-queries.md`](./stream-continuous-queries.md) for consumers and projections.
