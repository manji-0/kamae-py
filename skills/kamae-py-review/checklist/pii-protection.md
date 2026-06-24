# PII Protection Checklist
Reference: [`../../kamae-py/references/pii-protection.md`](../../kamae-py/references/pii-protection.md).
Also see [`../../kamae-py/references/loggable-identifiers.md`](../../kamae-py/references/loggable-identifiers.md).

## 5.1 Are PII and secrets wrapped or redacted? - High

Flag bare `str`, `bytes`, or primitive fields carrying email, phone, address, names, government IDs, payment data, health data, IP addresses, precise location, tokens, or passwords.

Suggest `pydantic.SecretStr`, project-local redacting wrappers, or explicit adapter-only exposure.

Do not require `SecretStr` for every PII value. Non-secret identifiers may use domain types if `repr`, logs, and serialization are redacted or intentionally exposed.

## 5.2 Can repr, str, logs, or errors expose sensitive data? - High

Flag default `repr`, f-string logging, formatted errors, or logs that include raw sensitive values.

Also check metrics, span attributes, audit events, and validation errors for raw PII or secrets.

## 5.3 Is plaintext exposure narrow and named? - Medium

Flag broad properties or getters such as `email` returning raw sensitive values. Suggest adapter-specific exposure methods or wrappers.

## 5.4 Is observability redacted by default? - High

Flag logging/metrics helpers that accept arbitrary domain objects or DTOs without redaction policy, allowlist fields, or explicit safe display wrappers.

## 5.5 Are person-linked IDs treated as conditional, not automatically safe? - High

Cross-check with [`../../kamae-py/references/loggable-identifiers.md`](../../kamae-py/references/loggable-identifiers.md). Flag `user_id`, `passenger_id`, `customer_id`, `patient_id`, `device_id`, or partner references logged without evidence that the value is an opaque surrogate.

Do not flag internal aggregate IDs such as `request_id`, `order_id`, or `correlation_id` when they are clearly surrogate keys with safe formatting.
