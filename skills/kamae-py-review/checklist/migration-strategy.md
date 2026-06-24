# Migration Strategy Checklist

Reference: [`../../kamae-py/references/migration-strategy.md`](../../kamae-py/references/migration-strategy.md).

## 19.1 Does the diff improve boundaries before rewriting everything? - Medium

Flag large rewrites that move legacy service classes without first tightening DTO parsing, state typing, or error mapping on the touched workflow.

## 19.2 Are compatibility shims thin and temporary? - Low

Flag broad adapter layers that permanently duplicate domain logic or preserve invalid states for convenience.

## 19.3 Is legacy code clearly isolated? - Medium

Flag new Kamae-style modules that still depend on untyped dicts, mutable globals, or ORM entities from the old layer without a documented seam.

## 19.4 Does the migration preserve observability and PII posture? - High

Flag migrated paths that keep old logging of raw payloads, drop redaction, or bypass transaction/outbox guarantees that existed or are required in the new design.

Cross-check [`pii-protection.md`](./pii-protection.md) and [`persistence-events.md`](./persistence-events.md).
