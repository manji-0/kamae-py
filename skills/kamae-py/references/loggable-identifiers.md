<!-- constrained-by ./pii-protection.md -->
<!-- derived-from ./logging-metrics.md -->

# Loggable Identifier Criteria

Use this reference when deciding which IDs may appear in logs, traces, errors, metrics, and domain events.

The default stance is **redact by default**. An identifier is loggable only when it passes the tests below and is recorded in an allowed channel.

## Three Questions

Ask these in order:

1. **Does the value identify a person, household, or account holder directly or by easy lookup?**
   If yes, treat it as sensitive unless an explicit audit or compliance path documents otherwise.
2. **Is the channel bounded and access-controlled?**
   Logs and traces inside a trusted backend are different from client-visible errors, metrics labels, or third-party exports.
3. **Does the channel need low cardinality?**
   Metrics, alert names, task names, and queue names must never carry per-request or per-user IDs.

If any answer blocks the channel, redact or hash the identifier.

## Identifier Tiers

| Tier | Meaning | Logs / traces | Errors (client-visible) | Metrics labels | Message strings |
| --- | --- | --- | --- | --- | --- |
| **A — Secrets** | Credentials and session material | Never | Never | Never | Never |
| **B — Direct PII** | Names, email, phone, address, government ID, payment PAN, health data, precise location | Never | Never | Never | Never |
| **C — Correlation** | System-generated IDs for one workflow or aggregate | OK in structured attributes | Usually no; use opaque error codes | Never | Never |
| **D — Account / actor** | IDs that map to users, customers, drivers, tenants, or devices | OK in structured attributes when ops need them | No unless required and documented | Never | Never |
| **E — Vocabulary** | Bounded enums and state kinds | OK | OK | OK | OK |

### Tier A — Never log

- Passwords, API keys, OAuth tokens, session cookies, refresh tokens
- Signing keys, webhook secrets, encryption keys
- `SecretStr` / `SecretBytes` plaintext from `get_secret_value()`

Use `SecretStr`, `Redacted`, or adapter-only exposure. Do not place these in `extra`, span attributes, errors, or events unless the event is an encrypted audit record with documented retention.

### Tier B — Never log

- Person names, email addresses, phone numbers, postal addresses
- Government IDs, payment card numbers, bank account numbers
- Health data, biometric identifiers
- Precise GPS coordinates, full street addresses
- Raw IP addresses in user-facing systems (treat as sensitive by default)

If a workflow needs contact data, keep it in the adapter that sends email/SMS/payment and out of general application logs.

### Tier C — Correlation IDs (logs and traces yes, metrics no)

These are **usually safe** in structured log `extra` fields and trace span attributes when your log backend is access-controlled:

- `request_id`, `order_id`, `aggregate_id`, `event_id`, `idempotency_key`
- `correlation_id`, `trace_id`, `span_id`, `causation_id`
- Internal surrogate keys with no published lookup API (for example a UUID primary key for a trip request)

Rules:

- Record them as **named structured fields**, not interpolated into the log message.
- Do not use them as metric labels, span names, task names, or cache keys.
- Do not assume they are anonymous; treat them as operational data with retention and access controls.

### Tier D — Account / actor IDs (conditional)

These **link to accounts or people** and need tighter rules:

- `passenger_id`, `driver_id`, `customer_id`, `user_id`, `account_id`
- `tenant_id`, `organization_id`, `device_id`, `session_id`
- External provider IDs (`stripe_customer_id`, OAuth `sub`, loyalty numbers)

Default rules:

- **Logs / traces:** allowed in structured attributes when operators must correlate support tickets, fraud review, or lifecycle debugging.
- **Errors returned to clients:** use opaque error codes; do not echo these IDs unless the API contract explicitly exposes them.
- **Metrics:** never use as labels.
- **Message strings:** never interpolate; use structured fields only.
- **Cross-boundary export:** hash or tokenize when logs leave the production trust zone (for example to a vendor SIEM, support tooling, or long-term cold storage).

When two Tier D IDs together make re-identification easier (for example `passenger_id` + `driver_id` on the same line), log the minimum set needed for the task. Prefer the aggregate `request_id` when it is enough.

### Tier E — Vocabulary (safe everywhere)

Low-cardinality values from a closed set:

- `kind`, `state_kind`, `source_kind`, `target_kind`
- `transition`, `event_name`, `error_kind`, `outcome`
- HTTP method, route template, tenant plan tier, region code (when the set is small and fixed)

These are the primary inputs for metrics labels and alert grouping.

## Channel Rules

| Channel | Allowed content | Avoid |
| --- | --- | --- |
| Log message text | Stable business fact in plain language | IDs, PII, payloads, `model_dump_json()` |
| Log `extra` / OTel log attributes | Tier C, Tier D (as needed), Tier E | Tier A, Tier B, whole model dumps |
| Trace span attributes | Same as log `extra` | Tier A, Tier B, high-cardinality IDs as span names |
| Metric labels | Tier E only | Any per-request or per-user ID |
| Domain errors (in-process) | Tier C and Tier E; Tier D only when callers need them | Tier A, Tier B |
| Public API / RPC errors | Tier E codes and messages | Tier B; Tier D unless contract requires it |
| Domain events (persisted) | Tier C–E as required by the event contract | Tier A; Tier B only in dedicated audit events with retention docs |

## Decision Examples (Taxi Domain)

| Identifier | Tier | Log `extra` | Metric label | Notes |
| --- | --- | --- | --- | --- |
| `request_id` | C | Yes | No | Preferred key for lifecycle correlation |
| `event_id` | C | Yes | No | Good for outbox and replay debugging |
| `passenger_id` | D | When needed | No | Prefer `request_id` if sufficient |
| `driver_id` | D | When needed | No | Same as `passenger_id` |
| `transition` | E | Yes | Yes | `"assign_driver"` |
| `source_kind` / `target_kind` | E | Yes | Yes | `"waiting"` → `"en_route"` |
| `error_kind` | E | Yes | Yes | `"request_not_found"` |
| Passenger email | B | No | No | Adapter-only |
| OAuth access token | A | No | No | `SecretStr` only |

## Recommended Allowlist Pattern

Define one project-local allowlist used by logging helpers, trace attribute setters, and error mappers.

```python
LOGGABLE_CORRELATION_FIELDS = frozenset(
    {
        "request_id",
        "aggregate_id",
        "event_id",
        "idempotency_key",
        "correlation_id",
        "trace_id",
    }
)

LOGGABLE_ACTOR_FIELDS = frozenset(
    {
        "passenger_id",
        "driver_id",
        "tenant_id",
    }
)

METRIC_LABEL_FIELDS = frozenset(
    {
        "transition",
        "source_kind",
        "target_kind",
        "event_name",
        "error_kind",
        "outcome",
    }
)


def log_context(**fields: object) -> dict[str, object]:
    allowed = LOGGABLE_CORRELATION_FIELDS | LOGGABLE_ACTOR_FIELDS | METRIC_LABEL_FIELDS
    return {key: value for key, value in fields.items() if key in allowed}
```

Use the allowlist at the adapter boundary. Domain and use-case code should pass explicit field names rather than dumping models.

## Hashing When Logs Leave the Trust Zone

When logs or traces are replicated to vendors, analytics, or long-retention stores, replace Tier D values with a stable hash:

```python
import hashlib


def hash_for_export(value: str, *, pepper: str) -> str:
    digest = hashlib.sha256(f"{pepper}:{value}".encode()).hexdigest()
    return digest[:16]
```

Document the pepper rotation and whether support staff can reverse the mapping through an internal lookup tool.

## Tests

Observability tests should assert:

- Tier A and B values never appear in log output, span attributes, or metric labels.
- Tier C and D values appear only as structured fields, never inside message strings.
- Metric exports contain Tier E labels only.
- Public error responses do not leak Tier B or unexpected Tier D values.

See [`test-data.md`](./test-data.md) for fixture guidance.
