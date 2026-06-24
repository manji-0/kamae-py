---
name: kamae-py
description: |
  Robust server-side Python domain modeling with Pydantic v2 discriminated unions,
  Python 3.12+, uv-managed projects, frozen state models, pure state transition
  functions, boundary validation, explicit domain errors, PII redaction,
  persistence/event consistency, logging and metrics, tests, documentation contracts,
  and quality gates.

  Use when writing or reviewing Python backend domain models, use cases, state
  transitions, repository protocols, API/DB/message boundary parsing, PII handling,
  outbox/event workflows, logging, metrics, tests, or Pydantic v2 unions for business
  workflows. Skip for frontend code, scripts unrelated to domain logic, infrastructure-only
  work, or Pydantic v1 projects unless migrating to v2.
---

# Kamae Python

Kamae Python is a stance for server-side Python 3.12+ code where uv manages the project, Pydantic v2 models describe domain states, `kind` discriminates unions, and state changes are pure functions.

## First Steps

1. Inspect `pyproject.toml`, `.python-version`, `uv.lock`, Ruff/mypy/pyright/pytest config, framework, and existing domain patterns.
2. Default to `.python-version` containing a 3.12.x or 3.13.x version, `requires-python = ">=3.12,<3.14"`, and `pydantic>=2,<3` managed by uv. Prefer Pydantic **2.11+** when using PEP 695 generic models such as `TransitionOutcome[TState, TEvent]` (see [`state-transitions.md`](./references/state-transitions.md)).
3. Default to mypy with the Pydantic v2 plugin: `plugins = ["pydantic.mypy"]` plus strict plugin flags under `[tool.pydantic-mypy]`.
4. Use `uv add`, `uv add --dev`, `uv lock`, and `uv run ...`; do not introduce `pip`, `requirements.txt`, Poetry, or Pipenv unless the repository already standardizes on them.
5. If `pydantic` is absent or version 1.x, ask before migrating existing code. For new code, add Pydantic v2 through uv.
6. Use Python 3.12+ syntax directly: `A | B`, `match`, `typing.assert_never` (3.11+), `typing.Self` (3.11+), and modern standard-library typing.
7. Keep generated code consistent with existing module layout, naming, and dependency choices unless they conflict with the principles below.
8. Read only the reference files needed for the current task.

## Reading Paths

Pick the path that matches the task. Read documents in order; skip steps already applied in the codebase.

### Greenfield domain work

1. [`domain-modeling.md`](./references/domain-modeling.md)
2. [`state-transitions.md`](./references/state-transitions.md)
3. [`boundary-defense.md`](./references/boundary-defense.md) and [`error-handling.md`](./references/error-handling.md)
4. [`aggregates.md`](./references/aggregates.md) and [`persistence-events.md`](./references/persistence-events.md)
5. [`taxi-request.py`](./references/taxi-request.py) for a compact end-to-end example
6. [`quality-gates.md`](./references/quality-gates.md) before finishing

### Brownfield migration

1. [`migration-strategy.md`](./references/migration-strategy.md)
2. [`boundary-defense.md`](./references/boundary-defense.md)
3. [`orm-adapters.md`](./references/orm-adapters.md) when persistence uses an ORM
4. Continue the greenfield path per migrated workflow

### Observability and PII only

1. [`pii-protection.md`](./references/pii-protection.md)
2. [`loggable-identifiers.md`](./references/loggable-identifiers.md)
3. [`logging-metrics.md`](./references/logging-metrics.md)
4. [`test-data.md`](./references/test-data.md) for observability test assertions

## Canonical Examples

Avoid copying full snippets into new references. Link to these **canonical** definitions instead:

| Topic | Canonical reference |
| --- | --- |
| Happy-path use case | [`state-transitions.md`](./references/state-transitions.md#keep-use-cases-thin) |
| Persistence error mapping | [`error-handling.md`](./references/error-handling.md#preferred-pattern-early-return) |
| Repository ports (production) | [`persistence-events.md`](./references/persistence-events.md#keep-repository-protocols-small) |
| Repository ports (intro) | [`domain-modeling.md`](./references/domain-modeling.md#define-repository-ports-with-protocols) |
| End-to-end code | [`taxi-request.py`](./references/taxi-request.py) |
| Mypy / Pydantic plugin config | [`domain-modeling.md`](./references/domain-modeling.md#configure-mypy-with-the-pydantic-plugin) |
| Quality gate commands | [`quality-gates.md`](./references/quality-gates.md#baseline-commands) |

## Principles

### Domain Modeling

Read [`references/domain-modeling.md`](./references/domain-modeling.md) when defining aggregate states, value objects, identifiers, repository protocols, or Pydantic discriminated unions.

Default to frozen Pydantic v2 state variants with a literal `kind` field and an `Annotated[A | B, Field(discriminator="kind")]` union. Use `TypeAdapter` as the runtime parser for union-shaped data.

For lightweight in-process value objects, read the Pydantic vs `dataclasses` / attrs selection table. For nominal ID wrappers and `__init_subclass__` patterns, read the strengthened value-type section in the same file. Keep decorators from hiding I/O, caching, or validation that pure transitions should receive as explicit arguments.

Read [`references/pydantic-performance.md`](./references/pydantic-performance.md) when validation overhead matters on large models, high-frequency endpoints, `model_construct` tradeoffs, or msgspec-style boundary serializers.

### State Transitions

Read [`references/state-transitions.md`](./references/state-transitions.md) when implementing transitions, use cases, domain events, or exhaustive branching.

Represent each valid transition as a pure function whose input type is the allowed source state and whose return type is the target state. Inject time, IDs, and randomness as arguments.

### Boundary Defense

Read [`references/boundary-defense.md`](./references/boundary-defense.md) when accepting API payloads, DB rows, env vars, files, queue messages, or external SDK responses.

Parse external data at the edge with Pydantic v2. Do not use `typing.cast`, broad `Any`, or unchecked dict access to turn unknown data into domain models.

### Error Handling

Read [`references/error-handling.md`](./references/error-handling.md) when modeling use-case failures, mapping errors to HTTP responses, async `Result` flows, or deciding whether to raise exceptions.

Keep expected domain failures explicit and use-case-specific. Reserve exceptions for framework boundaries, unexpected infrastructure failures, and programmer errors.

### Logging and Metrics

Read [`references/logging-metrics.md`](./references/logging-metrics.md) when adding logs, metrics, traces, or observability around domain objects, state transitions, use cases, or domain events.

Read [`references/loggable-identifiers.md`](./references/loggable-identifiers.md) for the allowlist tiers that separate correlation IDs, account IDs, and metric-safe vocabulary.

Default to OpenTelemetry for logs, metrics, and traces. Use OTLP to a collector as the primary export path; Prometheus `/metrics` and other pull-style interfaces are optional. Log meaningful messages, the state of the target domain object, and transition context when the operation changes lifecycle state. Keep metric names stable and labels low-cardinality. Derive metrics from domain events when possible.

### PII Protection

Read [`references/pii-protection.md`](./references/pii-protection.md) when domain models, DTOs, logs, metrics, errors, traces, or events contain personal data, credentials, tokens, or customer-identifying fields.

Read [`references/loggable-identifiers.md`](./references/loggable-identifiers.md) when deciding which IDs may appear in logs, traces, errors, metrics, or events.

Redact by default. Make plaintext exposure explicit and adapter-specific.

### Persistence and Events

Read [`references/persistence-events.md`](./references/persistence-events.md) when designing repositories, transactions, outbox records, idempotent commands, optimistic locking, or event payloads.

Persist aggregate state and emitted events atomically. Add DB constraints for invariants that the database can enforce.

Read [`references/aggregates.md`](./references/aggregates.md) when choosing aggregate roots, consistency boundaries, optimistic vs pessimistic locking, or cross-aggregate workflows.

### Application Wiring

Read [`references/application-wiring.md`](./references/application-wiring.md) when wiring use cases to repository ports, framework entrypoints, fakes, or deciding between explicit arguments and DI containers.

Prefer explicit function parameters and `typing.Protocol` ports. Wire dependencies only at the composition root.

Read [`references/concurrency.md`](./references/concurrency.md) when CPU-bound domain work, the GIL, `ProcessPoolExecutor`, or blocking the asyncio event loop is a concern.

### Infrastructure Resilience

Read [`references/infrastructure-resilience.md`](./references/infrastructure-resilience.md) when adding retry, timeout, or circuit-breaker behavior around external API, database, or queue adapters.

Keep tenacity, circuit breakers, and client timeouts in infrastructure modules. Pair retries with idempotency keys from [`references/persistence-events.md`](./references/persistence-events.md).

### Migration Strategy

Read [`references/migration-strategy.md`](./references/migration-strategy.md) when introducing Kamae Python into an existing class-based or ORM-centric codebase.

Migrate one workflow at a time. Improve boundary parsing before rewriting every service class.

Read [`references/orm-adapters.md`](./references/orm-adapters.md) for concrete SQLAlchemy 2.0 and Django ORM mapper patterns between persistence entities and Pydantic domain models.

### Test Data

Read [`references/test-data.md`](./references/test-data.md) when adding fixtures, factories, property-based tests (Hypothesis), transition tests, boundary tests, or persistence retry tests.

Tests should exercise the same constructors, Pydantic adapters, and transition functions as production code.

### Native and Unsafe Boundaries

Read [`references/unsafe-boundaries.md`](./references/unsafe-boundaries.md) when touching `ctypes`, `cffi`, native extensions, generated bindings, `model_construct`, broad casts, unchecked bytes, or other code that can bypass Python/Pydantic invariants.

Keep unsafe or unchecked operations outside domain logic and hide them behind small validated APIs.

### API Contracts

Read [`references/api-contracts.md`](./references/api-contracts.md) when documenting public domain APIs, repository protocols, transition functions, DTO conversion, event schemas, or safe wrappers.

Docstrings should explain invariants, accepted construction paths, errors, side effects, transaction expectations, and redaction behavior.

### Quality Gates

Read [`references/quality-gates.md`](./references/quality-gates.md) before finishing changes to domain, boundary, PII, persistence, tests, or sample code.

Prefer `uv run ruff format`, `uv run ruff check`, `uv run mypy`, and focused `uv run pytest` commands for touched code.

### Development Environment Setup

Read [`references/development-setup.md`](./references/development-setup.md) when setting up a local workspace to work on or with the Kamae Python skill.

Install uv, run `uv python install` and `uv sync`, then run the full local quality gate list before committing. Keep dependency changes in their own commit and regenerate `uv.lock`.

### Local Validation Setup

Read [`references/local-validation.md`](./references/local-validation.md) when bootstrapping local `pyproject.toml`, `.gitignore`, mypy/Pydantic plugin settings, Ruff, pytest, or skill-package validation.

Use [`scripts/apply_templates.py`](./scripts/apply_templates.py) to copy templates from [`assets/templates/`](./assets/templates/), or merge the templates manually. Repo-root files are not guaranteed to be installed with the skill.

After bootstrapping, run [`scripts/check_kamae_policy.py`](./scripts/check_kamae_policy.py) as a lightweight sanity check that the project matches the Kamae Python stance. It is advisory by default; use `--strict` to treat warnings as errors.

### CI Setup

Read [`references/ci-setup.md`](./references/ci-setup.md) when creating or updating GitHub Actions, branch protection guidance, or repository validation jobs.

CI should run the same uv-backed quality gates as local development and fail on lockfile drift.

## Worked Example

Read [`references/taxi-request.py`](./references/taxi-request.py) when a compact end-to-end example would help. It shows Pydantic v2 discriminated unions, frozen state models, pure transitions, domain events, and boundary parsing.

## Applying the Stance

Use judgment. If an existing codebase has a documented alternative pattern, follow it unless it weakens boundary validation or makes invalid states easy to represent. When deviating from these principles in new code, leave a short comment explaining the constraint.

For brownfield codebases, start with [`references/migration-strategy.md`](./references/migration-strategy.md) instead of attempting a full rewrite.
