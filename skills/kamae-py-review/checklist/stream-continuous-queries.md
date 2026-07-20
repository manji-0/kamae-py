# Streams and Continuous Queries Checklist

Reference: [`../../kamae-py/references/stream-continuous-queries.md`](../../kamae-py/references/stream-continuous-queries.md).

## 23.1 Are change feeds modeled as async-iterator ports? - Medium

Flag hand-rolled `while True: sleep; query` workers when a typed `AsyncIterator` / `Protocol` port would clarify backpressure, cancellation, and test doubles.

## 23.2 Do subscriptions start from a durable cursor? - High

Flag in-memory-only broadcast or subscriptions that cannot resume after restart without reprocessing or skipping events.

## 23.3 Are projection handlers idempotent? - High

Flag continuous-query or event handlers that apply side effects without deduplicating on event ID, `(aggregate_id, sequence)`, or an equivalent idempotency key.

## 23.4 Is backpressure handled? - Medium

Flag unbounded buffers between pollers and handlers, or producers that keep reading after the consumer cancelled or dropped.

## 23.5 Do read-side streams mutate write-model aggregates? - High

Flag projections that call aggregate transition methods or persist authoritative write-model state outside the command path.

## 23.6 Are unknown event versions handled explicitly? - Medium

Cross-check [`service-boundaries.md`](./service-boundaries.md). Flag handlers that raise unhandled exceptions or silently ignore unsupported event types when events are stored asynchronously.
