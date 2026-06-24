# Infrastructure Resilience Checklist

Reference: [`../../kamae-py/references/infrastructure-resilience.md`](../../kamae-py/references/infrastructure-resilience.md).

## 16.1 Are retries kept in infrastructure adapters? - Medium

Flag retry decorators, sleep loops, or circuit breakers inside domain modules or transition functions.

## 16.2 Are retries paired with idempotency? - High

Flag retried commands, outbox processors, or external API calls that can double-apply side effects without idempotency keys or dedupe records.

Cross-check [`persistence-events.md`](./persistence-events.md).

## 16.3 Are timeouts and circuit breakers explicit? - Medium

Flag unbounded HTTP/DB/queue calls from adapters when the project documents timeout and breaker expectations.

## 16.4 Do resilience policies hide domain failures? - Medium

Flag broad retry-on-any-exception behavior that can mask validation failures, authorization denials, or business-rule rejections that should not be retried.
