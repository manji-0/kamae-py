---
name: kamae-py-review
description: |
  Adversarial review of server-side Python domain code for Kamae principles:
  Pydantic v2 discriminated unions, frozen state models, pure state transitions,
  explicit domain errors, validated boundaries, PII redaction, persistence/event
  consistency, logging and metrics, docstring API contracts, and uv-backed quality
  gates. Use when reviewing Python pull requests, diffs, audits, or quality checks
  involving domain models, use cases, repository protocols, DTO conversion, ORM
  adapters, service/queue boundaries, stream/projection consumers, native/ctypes
  boundaries, Hypothesis tests, or business logic. Skip frontend assets, scripts
  unrelated to domain behavior, pure infrastructure, and Pydantic v1 projects
  unless the diff is migrating to v2.
---

# Kamae Python Review

Review Python code against the knowledge base in `../kamae-py/`. Prioritize bugs, invalid states, data leaks, and missing tests over style.

## Step 0: Load Applicable Rules

Read matching rule files in priority order:

1. `.claude/rules/*.md` and `.codex/rules/*.md` in the project root
2. `~/.claude/rules/*.md` and `~/.codex/rules/*.md`
3. `../../rules/defaults/*.md` relative to this `SKILL.md`

Skip rules unless `applies-to` is `kamae-py-review` or `*`. A `check-toggle` rule with `enabled: false` disables the named check. A `convention` rule changes review expectations.

## Review Procedure

1. Read [`../kamae-py/SKILL.md`](../kamae-py/SKILL.md).
2. Read `pyproject.toml`, `.python-version`, `uv.lock`, and relevant references under `../kamae-py/references/`.
3. If available, run `python3 skills/kamae-py-review/scripts/review_probe.py <changed Python paths>` from the repository root. Treat the output as review leads, not findings.
4. Read the Python files under review.
5. Choose checklist scope:
   - Full adversarial review: walk every checklist below in order.
   - Small/targeted diff: load only checklist files matched by the routing matrix, plus `tests.md` when behavior changes.
6. Report findings first, ordered by severity. Include `path:line`, risk, principle reference, evidence, and a concrete fix.

Example finding:

```text
High — src/application/assign_driver.py:42
Principle: error-handling §Keep Expected Failures Explicit
Evidence: `waiting = repo.get_waiting(request_id); waiting.driver_id = driver_id` mutates a frozen domain model through a broad dict fallback when the row is missing.
Fix: load through `TypeAdapter`, reject missing rows with `AssignDriverError.request_not_found`, and call `assign_driver(waiting, driver_id, now)` instead of mutating fields.
```

## Document Map

Checklist item numbers (`N.M`) match the checklist order below. Each checklist
links to its topic guide under `../kamae-py/references/`.

| # | Checklist | Topic guide |
| --- | --- | --- |
| 1 | `domain-modeling.md` | `domain-modeling.md` |
| 2 | `state-transitions.md` | `state-transitions.md` |
| 3 | `error-handling.md` | `error-handling.md` |
| 4 | `boundary.md` | `boundary-defense.md` |
| 5 | `pii-protection.md` | `pii-protection.md` |
| 6 | `logging-metrics.md` | `logging-metrics.md` |
| 7 | `unsafe-boundaries.md` | `unsafe-boundaries.md` |
| 8 | `quality-gates.md` | `quality-gates.md` |
| 9 | `api-contracts.md` | `api-contracts.md` |
| 10 | `ci-setup.md` | `ci-setup.md` |
| 11 | `development-setup.md` | `development-setup.md` |
| 12 | `persistence-events.md` | `persistence-events.md` |
| 13 | `aggregates.md` | `aggregates.md` |
| 14 | `application-wiring.md` | `application-wiring.md` |
| 15 | `concurrency.md` | `concurrency.md` |
| 16 | `infrastructure-resilience.md` | `infrastructure-resilience.md` |
| 17 | `orm-adapters.md` | `orm-adapters.md` |
| 18 | `pydantic-performance.md` | `pydantic-performance.md` |
| 19 | `migration-strategy.md` | `migration-strategy.md` |
| 20 | `tests.md` | `test-data.md` |
| 21 | `python-performance.md` | `python-performance.md` |
| 22 | `service-boundaries.md` | `service-boundaries.md` |
| 23 | `stream-continuous-queries.md` | `stream-continuous-queries.md` |

## Review Probe

The optional probe at [`./scripts/review_probe.py`](./scripts/review_probe.py) scans Python files for patterns that commonly route to Kamae checklists: native/unchecked boundaries, lint suppressions, implicit time/randomness, Pydantic bypasses, PII terms, persistence/event code, service/queue boundaries, stream/projection consumers, asyncio operational risks, and docstring contract gaps.

Use probe output only to choose what to inspect. Do not report a finding until you have read the relevant code and confirmed a reachable invariant break, leak, unsoundness risk, or project-policy violation.

## Review Routing Matrix

| Diff signal | Load checklists |
| --- | --- |
| New/changed domain types, value objects, Pydantic states, constructors, mutators, monetary/time/unit fields | `domain-modeling.md`, `state-transitions.md`, `tests.md` |
| State-machine transitions, lifecycle/status changes, optimistic locking, command handlers | `state-transitions.md`, `aggregates.md`, `persistence-events.md`, `tests.md` |
| Exceptions, Result values, domain error enums, infrastructure error mapping | `error-handling.md`, `tests.md` |
| `async def` use cases, `await`, port calls, lock usage across await | `error-handling.md`, `application-wiring.md`, `concurrency.md`, `tests.md` |
| Use-case functions/classes, handler wiring, repository protocols, adapter injection | `application-wiring.md`, `persistence-events.md`, `tests.md` |
| HTTP/queue/CLI/config/DB input, DTOs, `TypeAdapter`, ORM row mapping | `boundary.md`, `domain-modeling.md`, `orm-adapters.md`, `tests.md` |
| PII/secrets/tokens, logging, tracing, metrics, errors, `repr`/`str` | `pii-protection.md`, `logging-metrics.md`, `tests.md` |
| `ctypes`, `cffi`, native extensions, `model_construct`, broad casts, unchecked bytes | `unsafe-boundaries.md`, `boundary.md`, `tests.md` |
| Ruff, mypy/pyright, `# type: ignore`, `noqa`, pytest gates, CI quality checks | `quality-gates.md`, nearby concern checklist, `tests.md` |
| Docstrings, public API contracts, repository protocol docs, event schemas | `api-contracts.md`, nearby concern checklist, `tests.md` |
| CI workflows, required checks, GitHub Actions, uv/ruff/mypy/pytest jobs, advisory checks | `ci-setup.md`, `quality-gates.md`, `tests.md` |
| Dev environment, fake ports, local test loop, docker-compose, `.env.example` | `development-setup.md`, `application-wiring.md`, `tests.md` |
| Repositories, transactions, DB constraints, outbox/events, retries/idempotency | `persistence-events.md`, `aggregates.md`, `state-transitions.md`, `tests.md` |
| SQLAlchemy/Django ORM entities, row mappers, session usage | `orm-adapters.md`, `boundary.md`, `persistence-events.md`, `tests.md` |
| CPU-bound work, GIL, `ProcessPoolExecutor`, blocking the asyncio event loop | `concurrency.md`, `application-wiring.md`, `tests.md` |
| Tenacity retries, circuit breakers, client timeouts around external APIs/DB/queues | `infrastructure-resilience.md`, `persistence-events.md`, `tests.md` |
| `model_construct`, validation overhead, msgspec boundary serializers | `pydantic-performance.md`, `boundary.md`, `tests.md` |
| Nested loops, batch/list processing, N+1 queries, `deepcopy`, hot-path string building | `python-performance.md`, `persistence-events.md`, `orm-adapters.md`, `tests.md` |
| Legacy service classes, gradual migration, compatibility shims | `migration-strategy.md`, `boundary.md`, `tests.md` |
| gRPC/protobuf/OpenAPI clients, cross-service HTTP, queue message schemas, `schema_version` | `service-boundaries.md`, `boundary.md`, `persistence-events.md`, `tests.md` |
| Outbox pollers, projections, `AsyncIterator` event feeds, Celery/ARQ/Kafka/Redis Streams consumers | `stream-continuous-queries.md`, `persistence-events.md`, `service-boundaries.md`, `tests.md` |
| `hypothesis`, property tests, fixtures, factories, transition tables | `tests.md`, nearby domain checklist |
| Test-only helpers, builders, fixtures, redaction assertions | `tests.md` |

Use nearby checklists when a diff crosses concerns. Do not load unrelated files just to restate generic advice.

## Checklist Order

- [`checklist/domain-modeling.md`](./checklist/domain-modeling.md)
- [`checklist/state-transitions.md`](./checklist/state-transitions.md)
- [`checklist/error-handling.md`](./checklist/error-handling.md)
- [`checklist/boundary.md`](./checklist/boundary.md)
- [`checklist/pii-protection.md`](./checklist/pii-protection.md)
- [`checklist/logging-metrics.md`](./checklist/logging-metrics.md)
- [`checklist/unsafe-boundaries.md`](./checklist/unsafe-boundaries.md)
- [`checklist/quality-gates.md`](./checklist/quality-gates.md)
- [`checklist/api-contracts.md`](./checklist/api-contracts.md)
- [`checklist/ci-setup.md`](./checklist/ci-setup.md)
- [`checklist/development-setup.md`](./checklist/development-setup.md)
- [`checklist/persistence-events.md`](./checklist/persistence-events.md)
- [`checklist/aggregates.md`](./checklist/aggregates.md)
- [`checklist/application-wiring.md`](./checklist/application-wiring.md)
- [`checklist/concurrency.md`](./checklist/concurrency.md)
- [`checklist/infrastructure-resilience.md`](./checklist/infrastructure-resilience.md)
- [`checklist/orm-adapters.md`](./checklist/orm-adapters.md)
- [`checklist/pydantic-performance.md`](./checklist/pydantic-performance.md)
- [`checklist/python-performance.md`](./checklist/python-performance.md)
- [`checklist/migration-strategy.md`](./checklist/migration-strategy.md)
- [`checklist/service-boundaries.md`](./checklist/service-boundaries.md)
- [`checklist/stream-continuous-queries.md`](./checklist/stream-continuous-queries.md)
- [`checklist/tests.md`](./checklist/tests.md)

## Severity Classes

- High: likely runtime failure, impossible state admitted, unvalidated external data, or PII leak.
- Medium: weak domain contract, non-exhaustive error/state handling, persistence consistency risk.
- Low: maintainability, idiom, or test-quality issue that does not immediately compromise correctness.

Escalate when the diff touches external boundaries, authorization/tenant isolation, money, irreversible lifecycle transitions, persistence/event atomicity, secrets, native soundness, FFI, misleading public API docs, CI gates that can let broken domain code merge, lint suppressions that hide correctness risks, or production observability. Downgrade when the risk is type-check contained, test-only, startup-only, internal to a trusted adapter, generated code, private helper docs, advisory CI, or blocked by a nearby invariant not visible at the flagged line. Do not report a finding without evidence that a realistic caller can reach the bad state or leak.

Required evidence:

- Show the bypass path or missing guard, not only the smell.
- Name the invariant or domain rule being broken.
- Confirm whether existing constructors, validators, DB constraints, auth checks, or tests already cover it.
- Prefer "no issue" over speculative style findings.

If no issues are found, say so clearly and mention residual risk or test gaps.
