# State Transitions Checklist
Reference: [`../../kamae-py/references/state-transitions.md`](../../kamae-py/references/state-transitions.md).

## 2.1 Do transition functions constrain source state by type? - Medium

Flag functions that accept a broad union or `dict` and then runtime-check the state when a specific frozen state type could be accepted.

Do not flag union dispatch at API, repository, serialization, or handler boundaries when they immediately delegate into typed state handlers.

## 2.2 Are domain branches exhaustive and future-proof? - Medium

Flag `match` expressions over domain unions or enums that use a bare `_` or `else` to hide future variants when each variant should be considered explicitly.

Suggest `typing.assert_never` for unreachable branches.

## 2.3 Are transitions pure unless side effects are explicit? - Medium

Flag state transitions that perform persistence, logging, or message publishing inside the transition function. Suggest returning state plus events and letting the use case coordinate effects.

## 2.4 Is time, randomness, and ID generation injected? - High

Flag `datetime.now`, `uuid4`, `random.*`, or `time.*` inside transition functions instead of receiving `now`, IDs, or random values as arguments.

## 2.5 Do mutators preserve invariants? - High

Flag setters, `model_copy(update=...)`, or partial update commands that can violate cross-field rules, lifecycle restrictions, totals, timestamps, ownership, or tenant scope.

## 2.6 Are authorization and tenant checks enforced before transitions? - High

Flag use cases that transition state before proving the actor, tenant, account, or capability is allowed to do so.

## 2.7 Are concurrent transitions protected? - High

Flag lifecycle or balance changes that can race without optimistic locking, version checks, unique constraints, idempotency keys, or serializable transactions.

Cross-check [`aggregates.md`](./aggregates.md) for versioned saves and transaction-boundary expectations.
