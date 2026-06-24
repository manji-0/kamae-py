# Kamae Python Rules

Customize how `kamae-py` and `kamae-py-review` apply per project. Rules are Markdown files with YAML frontmatter.

## Rule Locations

Highest priority first:

| Tier | Path |
| --- | --- |
| Project | `.claude/rules/*.md`, `.codex/rules/*.md` |
| User | `~/.claude/rules/*.md`, `~/.codex/rules/*.md` |
| Plugin defaults | `rules/defaults/*.md` |

Same `name` on a higher tier wins. Same `name` on the same tier is resolved by lexicographically last filename.

## Rule Schema

```yaml
---
name: <kebab-case identifier>
description: <one-line summary>
applies-to: kamae-py | kamae-py-review | "*"
type: library-preference | check-toggle | convention | override
alwaysApply: false
---
```

Required fields:

| Field | Schema |
| --- | --- |
| `name` | Kebab-case rule identifier. Same-name rules override by tier. |
| `description` | One-line summary for humans and package validators. |
| `applies-to` | `kamae-py`, `kamae-py-review`, or `"*"`. |
| `type` | `library-preference`, `check-toggle`, `convention`, or `override`. |
| `alwaysApply` | Boolean. Defaults should normally use `false`. |

Optional fields:

| Field | Schema |
| --- | --- |
| `check` | Canonical check ID or alias for `check-toggle` rules. |
| `enabled` | Boolean for `check-toggle`; use `false` to disable a check. |

## Canonical Check IDs

Review checklist headings define canonical numeric check IDs. Rule toggles may also use the aliases below when a project wants a stable semantic name.

| ID | Alias | Checklist |
| --- | --- | --- |
| `1.1` | `semantic-primitives` | Domain modeling |
| `1.2` | `invariant-bypass` | Domain modeling |
| `1.3` | `discriminated-unions` | Domain modeling |
| `1.4` | `dto-orm-domain-separation` | Domain modeling |
| `1.5` | `concept-organization` | Domain modeling |
| `1.6` | `explicit-money-time-units` | Domain modeling |
| `1.7` | `frozen-extra-forbid` | Domain modeling |
| `2.1` | `typed-source-state` | State transitions |
| `2.2` | `exhaustive-domain-match` | State transitions |
| `2.3` | `pure-transitions` | State transitions |
| `2.4` | `injected-time-randomness` | State transitions |
| `2.5` | `invariant-preserving-mutators` | State transitions |
| `2.6` | `auth-tenant-transition-guards` | State transitions |
| `2.7` | `concurrent-transition-protection` | State transitions |
| `3.1` | `explicit-business-failures` | Error handling |
| `3.2` | `no-assert-for-business-rules` | Error handling |
| `3.3` | `specific-domain-errors` | Error handling |
| `3.4` | `intentional-infra-error-mapping` | Error handling |
| `3.5` | `async-use-case-layering` | Error handling |
| `3.6` | `no-lock-across-await` | Error handling |
| `3.7` | `meaningful-error-variants` | Error handling |
| `3.8` | `exception-chain-preservation` | Error handling |
| `3.9` | `error-message-redaction` | Error handling |
| `4.1` | `boundary-dto-domain-conversion` | Boundary defense |
| `4.2` | `pydantic-is-not-only-validator` | Boundary defense |
| `4.3` | `external-format-overconfigure` | Boundary defense |
| `4.4` | `dto-defaults-unknown-fields` | Boundary defense |
| `4.5` | `no-unchecked-casts` | Boundary defense |
| `4.6` | `auth-tenant-boundary-checks` | Boundary defense |
| `5.1` | `sensitive-wrapper` | PII protection |
| `5.2` | `pii-repr-log-redaction` | PII protection |
| `5.3` | `narrow-plaintext-exposure` | PII protection |
| `5.4` | `observability-redaction` | PII protection |
| `5.5` | `person-linked-id-policy` | PII protection |
| `6.1` | `meaningful-log-messages` | Logging and metrics |
| `6.2` | `log-domain-object-state` | Logging and metrics |
| `6.3` | `transition-logging` | Logging and metrics |
| `6.4` | `structured-log-levels` | Logging and metrics |
| `6.5` | `domain-outcome-metrics` | Logging and metrics |
| `6.6` | `metric-cardinality` | Logging and metrics |
| `6.7` | `observability-pii-redaction` | Logging and metrics |
| `6.8` | `logged-id-classification` | Logging and metrics |
| `6.9` | `error-chain-logging` | Logging and metrics |
| `6.10` | `bounded-error-metrics` | Logging and metrics |
| `7.1` | `no-native-domain-logic` | Unsafe boundaries |
| `7.2` | `safe-native-abstraction` | Unsafe boundaries |
| `7.3` | `native-safety-docs` | Unsafe boundaries |
| `7.4` | `native-does-not-bypass-domain` | Unsafe boundaries |
| `7.5` | `native-boundary-tests` | Unsafe boundaries |
| `8.1` | `ruff-format-clean` | Quality gates |
| `8.2` | `lint-typecheck-clean` | Quality gates |
| `8.3` | `narrow-suppressions` | Quality gates |
| `8.4` | `suppression-domain-risk` | Quality gates |
| `8.5` | `quality-gates-in-ci` | Quality gates |
| `9.1` | `docstring-public-contracts` | API contracts |
| `9.2` | `docstring-errors-native` | API contracts |
| `9.3` | `docstring-safe-examples` | API contracts |
| `9.4` | `docstring-maintenance` | API contracts |
| `9.5` | `docstring-check-scope` | API contracts |
| `10.1` | `ci-required-reviewer-checks` | CI setup |
| `10.2` | `ci-representative-matrix` | CI setup |
| `10.3` | `ci-risk-tied-safety-jobs` | CI setup |
| `10.4` | `ci-advisory-check-clarity` | CI setup |
| `10.5` | `ci-local-reproduction` | CI setup |
| `11.1` | `domain-free-of-framework-imports` | Development setup |
| `11.2` | `domain-tests-without-docker` | Development setup |
| `11.3` | `fixtures-through-constructors` | Development setup |
| `11.4` | `documented-local-check-loop` | Development setup |
| `11.5` | `no-secrets-in-env-files` | Development setup |
| `11.6` | `test-layout-matches-layers` | Development setup |
| `12.1` | `atomic-state-events` | Persistence and events |
| `12.2` | `use-case-repository-protocols` | Persistence and events |
| `12.3` | `adapter-does-not-invent-events` | Persistence and events |
| `12.4` | `db-constraints-mirror-invariants` | Persistence and events |
| `12.5` | `idempotent-retry-handling` | Persistence and events |
| `12.6` | `event-versioning` | Persistence and events |
| `13.1` | `use-case-transaction-boundary` | Aggregates |
| `13.2` | `root-only-invariant-changes` | Aggregates |
| `13.3` | `optimistic-concurrency` | Aggregates |
| `13.4` | `pessimistic-lock-scope` | Aggregates |
| `13.5` | `cross-aggregate-coordination` | Aggregates |
| `13.6` | `idempotent-command-boundary` | Aggregates |
| `14.1` | `small-use-case-ports` | Application wiring |
| `14.2` | `use-cases-depend-on-ports` | Application wiring |
| `14.3` | `orchestration-in-use-cases` | Application wiring |
| `14.4` | `explicit-dependency-injection` | Application wiring |
| `14.5` | `tests-swap-ports` | Application wiring |
| `15.1` | `cpu-bound-off-event-loop` | Concurrency |
| `15.2` | `no-shared-mutable-domain-state` | Concurrency |
| `15.3` | `scoped-process-thread-pools` | Concurrency |
| `15.4` | `lock-session-scope` | Concurrency |
| `16.1` | `retries-in-infrastructure` | Infrastructure resilience |
| `16.2` | `retries-with-idempotency` | Infrastructure resilience |
| `16.3` | `explicit-timeouts-circuit-breakers` | Infrastructure resilience |
| `16.4` | `resilience-hides-domain-failures` | Infrastructure resilience |
| `17.1` | `orm-out-of-domain` | ORM adapters |
| `17.2` | `mapper-validates-both-ways` | ORM adapters |
| `17.3` | `session-owned-by-adapters` | ORM adapters |
| `17.4` | `no-lazy-loading-in-domain` | ORM adapters |
| `17.5` | `optimistic-lock-column-mapping` | ORM adapters |
| `18.1` | `model-construct-trusted-only` | Pydantic performance |
| `18.2` | `intentional-boundary-optimization` | Pydantic performance |
| `18.3` | `performance-preserves-invariants` | Pydantic performance |
| `19.1` | `boundaries-before-rewrite` | Migration strategy |
| `19.2` | `thin-compatibility-shims` | Migration strategy |
| `19.3` | `legacy-isolation` | Migration strategy |
| `19.4` | `migration-preserves-observability-pii` | Migration strategy |
| `20.1` | `constructor-conversion-tests` | Tests |
| `20.2` | `invalid-transition-tests` | Tests |
| `20.3` | `exhaustiveness-tests` | Tests |
| `20.4` | `mutator-invariant-tests` | Tests |
| `20.5` | `persistence-retry-tests` | Tests |
| `20.6` | `boundary-observability-tests` | Tests |
| `20.7` | `property-based-invariant-tests` | Tests |

Example disabling a check:

```yaml
---
name: allow-mutable-domain-during-migration
description: Permit mutable domain models while migrating one workflow to frozen states.
applies-to: kamae-py-review
type: check-toggle
check: invariant-bypass
enabled: false
alwaysApply: false
---
```

Rule bodies may add the rationale, scope, replacement convention, and sunset condition. Keep examples project-specific in project-level rules rather than plugin defaults.
