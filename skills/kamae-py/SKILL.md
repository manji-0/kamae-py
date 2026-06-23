---
name: kamae-py
description: |
  Robust server-side Python domain modeling with Pydantic v2 discriminated unions,
  Python 3.13.14, uv-managed projects, frozen state models, pure state transition
  functions, boundary validation, explicit domain errors, PII redaction,
  persistence/event consistency, tests, documentation contracts, and quality gates.

  Use when writing or reviewing Python backend domain models, use cases, state
  transitions, repository protocols, API/DB/message boundary parsing, PII handling,
  outbox/event workflows, tests, or Pydantic v2 unions for business workflows.
  Skip for frontend code, scripts unrelated to domain logic, infrastructure-only work,
  or Pydantic v1 projects unless migrating to v2.
---

# Kamae Python

Kamae Python is a stance for server-side Python 3.13.14 code where uv manages the project, Pydantic v2 models describe domain states, `kind` discriminates unions, and state changes are pure functions.

## First Steps

1. Inspect `pyproject.toml`, `.python-version`, `uv.lock`, Ruff/mypy/pyright/pytest config, framework, and existing domain patterns.
2. Default to `.python-version` containing `3.13.14`, `requires-python = ">=3.13.14,<3.14"`, and `pydantic>=2,<3` managed by uv.
3. Default to mypy with the Pydantic v2 plugin: `plugins = ["pydantic.mypy"]` plus strict plugin flags under `[tool.pydantic-mypy]`.
4. Use `uv add`, `uv add --dev`, `uv lock`, and `uv run ...`; do not introduce `pip`, `requirements.txt`, Poetry, or Pipenv unless the repository already standardizes on them.
5. If `pydantic` is absent or version 1.x, ask before migrating existing code. For new code, add Pydantic v2 through uv.
6. Use Python 3.13 syntax directly: `A | B`, `match`, `typing.assert_never`, `Self`, and modern standard-library typing.
7. Keep generated code consistent with existing module layout, naming, and dependency choices unless they conflict with the principles below.
8. Read only the reference files needed for the current task.

## Principles

### Domain Modeling

Read [`references/domain-modeling.md`](./references/domain-modeling.md) when defining aggregate states, value objects, identifiers, repository protocols, or Pydantic discriminated unions.

Default to frozen Pydantic v2 state variants with a literal `kind` field and an `Annotated[A | B, Field(discriminator="kind")]` union. Use `TypeAdapter` as the runtime parser for union-shaped data.

### State Transitions

Read [`references/state-transitions.md`](./references/state-transitions.md) when implementing transitions, use cases, domain events, or exhaustive branching.

Represent each valid transition as a pure function whose input type is the allowed source state and whose return type is the target state. Inject time, IDs, and randomness as arguments.

### Boundary Defense

Read [`references/boundary-defense.md`](./references/boundary-defense.md) when accepting API payloads, DB rows, env vars, files, queue messages, or external SDK responses.

Parse external data at the edge with Pydantic v2. Do not use `typing.cast`, broad `Any`, or unchecked dict access to turn unknown data into domain models.

### Error Handling

Read [`references/error-handling.md`](./references/error-handling.md) when modeling use-case failures, mapping errors to HTTP responses, or deciding whether to raise exceptions.

Keep expected domain failures explicit and use-case-specific. Reserve exceptions for framework boundaries, unexpected infrastructure failures, and programmer errors.

### PII Protection

Read [`references/pii-protection.md`](./references/pii-protection.md) when domain models, DTOs, logs, metrics, errors, traces, or events contain personal data, credentials, tokens, or customer-identifying fields.

Redact by default. Make plaintext exposure explicit and adapter-specific.

### Persistence and Events

Read [`references/persistence-events.md`](./references/persistence-events.md) when designing repositories, transactions, outbox records, idempotent commands, optimistic locking, or event payloads.

Persist aggregate state and emitted events atomically. Add DB constraints for invariants that the database can enforce.

### Test Data

Read [`references/test-data.md`](./references/test-data.md) when adding fixtures, factories, property tests, transition tests, boundary tests, or persistence retry tests.

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
