# PII Protection

## Redact by Default

Personal data and secrets should be hard to log accidentally. PII includes names, email addresses, phone numbers, addresses, government IDs, payment identifiers, health data, IP addresses, device identifiers, precise location, and tenant/customer identifiers when they can identify a person or account.

Credentials and secrets include passwords, API keys, OAuth tokens, session cookies, cryptographic material, signing keys, and webhook secrets.

Use small value objects or a project-local redacting wrapper for sensitive fields.

```python
from typing import Generic, TypeVar

from pydantic import SecretStr

T = TypeVar("T")


class Redacted(DomainModel, Generic[T]):
    value: T

    def __repr__(self) -> str:
        return "Redacted(value='***')"

    def __str__(self) -> str:
        return "***"


class CustomerContact(DomainModel):
    email: Redacted[str]
    phone: Redacted[str] | None = None


class PaymentGatewayCredentials(DomainModel):
    api_key: SecretStr
```

Prefer `SecretStr` / `SecretBytes` for credentials and a typed redaction wrapper for PII whose plaintext is sometimes needed.

## Keep Plaintext Exposure Narrow and Named

Expose sensitive values only at adapters that genuinely need them, such as email delivery, payment processors, encryption, audit export, or identity-provider calls. Name exposure methods for their purpose.

```python
class EmailAddress(DomainModel):
    value: str

    def expose_for_delivery(self) -> str:
        return self.value
```

Avoid broad getters such as `raw()`, `value`, or `as_str()` on sensitive values unless the project has a clear wrapper policy and review culture.

## Redact Logs, Metrics, Errors, and Events

Never format sensitive values into domain errors, exception messages, logs, tracing spans, metrics labels, task names, queue names, cache keys, or panic-style diagnostics.

Use allowlisted log fields rather than dumping whole Pydantic models. Read [`loggable-identifiers.md`](./loggable-identifiers.md) for the tiered criteria that separate secrets, direct PII, correlation IDs, account IDs, and metric-safe vocabulary.

```python
logger.info(
    "driver assignment rejected",
    extra={"request_id": str(request_id), "reason": error.kind},
)
```

If an event or audit record must include PII, document the retention, access, and redaction expectation in the event model docstring and keep its schema explicit.

## Serialization Policy

Use `model_dump` / `model_dump_json` intentionally. Do not serialize arbitrary domain objects into logs or metrics. For public responses, create response DTOs that include only fields intended for exposure.

Pydantic `SecretStr` redacts representation, but code can still expose plaintext through `get_secret_value()`. Treat that method as an adapter boundary and keep calls easy to audit.
