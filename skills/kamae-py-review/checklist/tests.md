# Tests Checklist
Reference: [`../../kamae-py/references/test-data.md`](../../kamae-py/references/test-data.md).

## 20.1 Do tests exercise constructors and conversions? - Medium

Flag tests that create invalid domain states through `model_construct`, raw dicts, or public field literals instead of constructors/builders/adapters.

Do not flag invalid construction in tests whose purpose is migration compatibility, deserialization hardening, corrupted-row handling, property shrinking, or negative-path coverage.

## 20.2 Are key invalid transitions covered? - Medium

Flag state-machine code without tests for rejected transitions, DTO conversion failures, and error mapping.

## 20.3 Are type and exhaustiveness guarantees tested when central to the design? - Low

Suggest mypy/pyright strict coverage or runtime `assert_never` tests only when static state safety is a core promise and the added cost is justified.

## 20.4 Are invariant-preserving mutators tested? - Medium

Flag new setters, patch commands, and update methods without tests for cross-field invariants, units, timestamps, and authorization/tenant rejection.

## 20.5 Are persistence and retry edges tested? - Medium

Flag repository/use-case changes without coverage for DB constraint failures, optimistic-lock conflicts, transaction rollback, duplicate commands, retry behavior, and outbox/event version compatibility.

## 20.6 Are boundary and observability failures tested? - Medium

Flag boundary changes without tests for unknown fields, defaulted fields, malformed DTOs, redacted logs/errors, and safe serialization of read models.

Cross-check [`../../kamae-py/references/loggable-identifiers.md`](../../kamae-py/references/loggable-identifiers.md) for identifier-tier assertions.

## 20.7 Are input-wide invariants covered with property tests? - Low

Cross-check [`../../kamae-py/references/test-data.md`](../../kamae-py/references/test-data.md). Suggest Hypothesis property tests when value-object validation, round trips, transition laws, or idempotency lack example-table coverage and generators can use public constructors.

Do not require property tests for small closed enums, trivial getters, or code already guarded by static state types.
