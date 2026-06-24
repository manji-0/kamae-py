# PII Protection

> **When to read:** Domain models, DTOs, logs, metrics, errors, traces, or events contain personal data, credentials, tokens, or customer-identifying fields.
> **Related:** [`loggable-identifiers.md`](./loggable-identifiers.md) (tier rules and channel policy), [`logging-metrics.md`](./logging-metrics.md), [`persistence-events.md`](./persistence-events.md).


Tiered allowlists and channel rules live in [`loggable-identifiers.md`](./loggable-identifiers.md). This document covers redaction wrappers and exposure policy.

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

## Logging Filter for Automatic Redaction

Defense in depth: even when developers use structured fields correctly, intercept formatted log records and redact known PII patterns before handlers emit them.

```python
import logging
import re
from typing import ClassVar


EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


class PiiRedactionFilter(logging.Filter):
    """Redact common PII patterns from log message text and string ``extra`` values."""

    _patterns: ClassVar[tuple[re.Pattern[str], ...]] = (EMAIL_RE, PHONE_RE)

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact(record.msg)
        if isinstance(record.args, dict):
            record.args = {k: self._redact(v) for k, v in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(self._redact(a) for a in record.args)
        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if isinstance(value, str):
                setattr(record, key, self._redact(value))
        return True

    def _redact(self, value: object) -> object:
        if not isinstance(value, str):
            return value
        redacted = value
        for pattern in self._patterns:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted


def configure_logging() -> None:
    root = logging.getLogger()
    root.addFilter(PiiRedactionFilter())
```

Notes:

- Filters complement—not replace—typed `Redacted` models and allowlisted `extra` keys.
- Add project-specific patterns (government IDs, internal account formats) explicitly.
- Do not log full `model_dump()` output; filters cannot recover structured discipline after the fact.
- Tier rules in [`loggable-identifiers.md`](./loggable-identifiers.md) still apply: never rely on regex alone for secrets in structured fields.

## OpenTelemetry Span Attributes

Exclude PII from span names, events, and attributes exported to vendors.

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan


class PiiScrubbingProcessor(SpanProcessor):
    _blocked_keys = frozenset({"email", "phone", "password", "authorization", "cookie"})

    def on_end(self, span: ReadableSpan) -> None:
        for key in list(span.attributes or {}):
            if key.lower() in self._blocked_keys:
                # Prefer not setting these attributes at instrumentation sites.
                pass


tracer = trace.get_tracer(__name__)


def record_assignment(request_id: UUID, reason: str) -> None:
    with tracer.start_as_current_span("assign_driver") as span:
        span.set_attribute("request_id", str(request_id))  # Tier C — OK
        span.set_attribute("reason", reason)  # bounded vocabulary — OK
        # span.set_attribute("passenger_email", ...)  # never
```

Practices:

- Span **names** must be low-cardinality (`assign_driver`, not `assign_driver:{user_id}`).
- Put Tier C/D IDs only in attributes when ops need them; block Tier A/B keys at code review.
- Use `trace.use_span` context in adapters, not inside pure transitions.
- For OTLP export to third parties, consider a `SpanExporter` wrapper that strips Tier D attributes entirely.

## GDPR Data Minimization in Event Payloads

Event schemas persist for years. Apply minimization at design time:

| Principle | Practice |
| --- | --- |
| Collect only what handlers need | Prefer IDs over names; fetch display fields from a read model at consume time |
| Avoid snapshotting contact data | Do not embed email/phone in `DriverAssigned` unless a downstream handler truly has no other lookup path |
| Document lawful basis | Note in the event class docstring when PII is intentional (audit, billing export) |
| Retention | Pair PII-bearing events with retention TTL or compaction jobs |
| Erasure | Design `aggregate_id` keys so erasure requests can target related event streams |

```python
class PassengerNotified(DomainModel):
    """Notify adapter that a message was sent.

    Redaction:
        Stores ``passenger_id`` only—not email or phone. The notify adapter loaded
        contact data from the identity service and must not log it.
    """

    event_name: Literal["passenger_notified"] = "passenger_notified"
    event_version: Literal[1] = 1
    event_id: UUID
    aggregate_id: UUID
    passenger_id: UUID
    channel: Literal["email", "sms", "push"]
```

Read [`persistence-events.md`](./persistence-events.md#event-schema-evolution) before adding fields to versioned events.

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

## Testing Redaction

Assert redaction at the wrapper and logging boundary—not only that code runs.

```python
def test_redacted_repr_masks_email() -> None:
    contact = CustomerContact(email=Redacted(value="user@example.com"))
    assert "user@example.com" not in repr(contact)
    assert "user@example.com" not in str(contact)


def test_secret_str_not_in_model_repr() -> None:
    creds = PaymentGatewayCredentials(api_key=SecretStr("sk_live_secret"))
    dumped = repr(creds)
    assert "sk_live_secret" not in dumped


def test_pii_filter_scrubs_message() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="contact user@example.com",
        args=(),
        exc_info=None,
    )
    assert PiiRedactionFilter().filter(record) is True
    assert "user@example.com" not in record.msg
    assert "[REDACTED]" in record.msg


def test_assign_driver_error_does_not_echo_pii(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        logger.info("failed", extra={"request_id": "...", "reason": "invalid_state"})
    for record in caplog.records:
        assert "@" not in record.getMessage()
```

Add regression tests when fixing a PII leak in production. Prefer checking `repr`, `str`, log `extra`, and HTTP response bodies for forbidden substrings.
