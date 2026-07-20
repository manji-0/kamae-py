# Service Boundaries Checklist

Reference: [`../../kamae-py/references/service-boundaries.md`](../../kamae-py/references/service-boundaries.md).

## 22.1 Are wire messages converted through DTO → domain? - High

Flag handlers that pass protobuf, JSON, or queue payloads directly into domain logic without `TypeAdapter` / Pydantic validation and constructor mapping.

## 22.2 Do generated client types leak into domain packages? - Medium

Flag domain or use-case modules importing `grpc` stubs, OpenAPI-generated models, or SDK response types instead of mapping at the adapter edge.

## 22.3 Is JSON/protobuf schema evolution explicit? - High

Flag breaking field renames/removals, missing `schema_version` / event version, or consumers that raise unhandled exceptions on unknown event types or versions.

## 22.4 Are queue handlers idempotent? - High

Cross-check [`persistence-events.md`](./persistence-events.md). Flag consumers that apply side effects without idempotency keys or dedupe storage.

## 22.5 Are retries, breakers, and rate limits in adapters? - Medium

Flag retry loops, circuit-breaker state, or rate limiting inside domain transitions or use-case business rules.

## 22.6 Is correlation context propagated on outbound calls? - Low

Flag cross-service calls or published messages that omit `correlation_id` or trace context when the ingress request already carried it.
