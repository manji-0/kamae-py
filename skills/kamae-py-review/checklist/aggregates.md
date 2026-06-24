# Aggregates Checklist

Reference: [`../../kamae-py/references/aggregates.md`](../../kamae-py/references/aggregates.md).

## 13.1 Does one use case own the transaction boundary? - High

Flag workflows that save state, emit events, or publish messages from multiple unrelated callers without a single use case coordinating the atomic unit of work.

## 13.2 Are aggregate invariants changed only through the root? - High

Flag code that mutates child entities or lifecycle state while bypassing the aggregate root's transition functions or typed state models.

## 13.3 Is optimistic concurrency handled for contested writes? - High

Flag load/modify/save paths on balances, lifecycle state, inventory, or other high-contention aggregates without version checks, compare-and-swap semantics, or equivalent DB constraints.

Map zero-row updates and version mismatches to typed errors such as `ConcurrentModification`, not silent success.

## 13.4 Is pessimistic locking scoped and justified? - Medium

Flag broad or long-held locks, especially across `await`, when optimistic concurrency or DB constraints would suffice. Escalate when lock scope is unclear or domain invariants can still race.

## 13.5 Is cross-aggregate coordination explicit? - Medium

Flag use cases or repositories that mutate two aggregate roots in memory and rely on callers to persist both. Suggest events, sagas, snapshots, or a documented single-transaction strategy.

## 13.6 Are retries and duplicate commands idempotent at the boundary? - High

Cross-check `persistence-events.md` and `tests.md`. Flag command handlers or consumers that can apply the same transition twice without an idempotency key or dedupe record.
