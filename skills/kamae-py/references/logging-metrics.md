<!-- constrained-by ./pii-protection.md -->
<!-- derived-from ./state-transitions.md -->

# Logging and Metrics

## Prefer OpenTelemetry for Telemetry Signals

Use **OpenTelemetry** as the default interface for logs, metrics, and traces. It gives the application a single, vendor-neutral model and lets operators route telemetry to collectors, backends, or local exporters without changing domain code.

Recommended packages when instrumenting:

- `opentelemetry-api` for the API surface.
- `opentelemetry-sdk` for the SDK and built-in exporters.
- `opentelemetry-exporter-otlp-proto-grpc` or `opentelemetry-exporter-otlp-proto-http` for OTLP export to a collector.

```python
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

resource = Resource.create({"service.name": "taxi-service"})
reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint="..."))
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
```

## Make Pull Interfaces Optional

`/metrics` for Prometheus, local pprof endpoints, and other pull-style exporters are **optional**. They are useful for local development, single-process deployments, or environments where a collector cannot be placed, but they are not the default requirement.

Use the OpenTelemetry Collector to translate OTLP into Prometheus remote-write or scrape format in production. If a pull endpoint is needed, add it as an explicit adapter or startup option rather than embedding an HTTP server inside domain code.

```python
# Optional: Prometheus pull endpoint only when enabled
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import start_http_server

reader = PrometheusMetricReader()
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
start_http_server(port=9099)
```

Keep domain and use-case code independent of the chosen export mechanism.

## Use Structured Logs Through OpenTelemetry

Attach log attributes the same way regardless of whether logs end up in OTLP, stdout, or a file. In Python this usually means a standard `logging.Logger` with an `extra` dictionary or an OpenTelemetry `LoggingHandler` that forwards records as OTLP log records.

```python
logger.info(
    "driver assigned",
    extra={
        "request_id": str(en_route.request_id),
        "transition": "assign_driver",
        "source_kind": waiting.kind,
        "target_kind": en_route.kind,
    },
)
```

Do not format sensitive values into the message string. Keep the message stable and put variable, non-sensitive context into attributes.

## Record Spans Around Use Cases and Adapters

Use OpenTelemetry traces to follow a command through its lifecycle: use-case invocation, authorization, transition, event creation, and persistence. Add span attributes from the same safe, allowlisted set used for logs and metrics.

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def assign_driver_use_case(...) -> Result[EnRoute, AssignDriverError]:
    with tracer.start_as_current_span("assign_driver_use_case") as span:
        span.set_attribute("request_id", str(request_id))
        ...
```

Keep span names stable and low-cardinality. Use attributes, not span names, for request-specific identifiers.

## Keep Logs, Metrics, and Domain Events Distinct

- **Domain events** describe business facts and are persisted as part of the aggregate's history.
- **Logs** are for operators: they explain what happened, to which object, and in which transition.
- **Metrics** are for dashboards and alerts: stable names, low-cardinality labels, and counts or durations.

Do not overload logs with business audit requirements, and do not build metrics by parsing log lines.

## Write Meaningful Log Messages

A log message should state the business fact in plain language. Prefer past-tense phrases that describe what happened rather than how the code executed.

```python
logger.info("driver assigned", extra={"request_id": ...})
logger.info("trip completed", extra={"request_id": ...})
```

Avoid messages that only echo the function name or encode internal branch names:

```python
# Avoid
logger.info("process_request called")
logger.info("in assign_driver_use_case")
```

## Log the Target Domain Object's State

Include the fields an operator needs to correlate and diagnose the event: usually identity, aggregate kind, and a small set of safe, non-sensitive attributes. Use structured `extra` fields rather than string interpolation.

```python
logger.info(
    "driver assigned",
    extra={
        "request_id": str(en_route.request_id),
        "passenger_id": str(en_route.passenger_id),
        "driver_id": str(en_route.driver_id),
        "state_kind": en_route.kind,
    },
)
```

Do not dump the whole Pydantic model. Model dumps may include PII, large nested structures, or unstable serialization of internal fields.

```python
# Avoid
logger.info(f"driver assigned: {en_route.model_dump_json()}")
```

## Include Transition Information for Transition Processing

When a log line accompanies a state change, include the transition name, the source state kind, and the target state kind. This makes it possible to follow an aggregate's lifecycle without reconstructing it from timestamps.

```python
logger.info(
    "driver assigned",
    extra={
        "request_id": str(en_route.request_id),
        "transition": "assign_driver",
        "source_kind": waiting.kind,
        "target_kind": en_route.kind,
    },
)
```

Return transition outcomes from pure transition functions, then log from the use case or adapter that orchestrated the change.

```python
async def assign_driver_use_case(...) -> Result[EnRoute, AssignDriverError]:
    ...
    en_route = assign_driver(waiting, driver_id, now)
    logger.info(
        "driver assigned",
        extra={
            "request_id": str(en_route.request_id),
            "transition": "assign_driver",
            "source_kind": waiting.kind,
            "target_kind": en_route.kind,
        },
    )
    ...
```

## Keep Logging Out of Pure Transition Functions

Transition functions should remain pure. They must not call loggers, read clocks, generate IDs, or perform I/O. Pass the outcome back to the caller and let the use case or adapter emit logs.

## Redact PII and Secrets by Default

Apply the same redaction rules as errors and events. Do not put request IDs, customer IDs, or driver IDs in log messages as formatted strings unless the project explicitly treats them as non-identifying. Even when safe, prefer structured `extra` fields.

Read [`pii-protection.md`](./pii-protection.md) for details on redacting names, contact information, credentials, tokens, and location data.

## Design Metrics with Stable Names and Low-Cardinality Labels

Metric names should be stable across deploys. Labels should come from a bounded domain vocabulary, not from user-generated or per-aggregate values.

Good labels for a taxi domain:

```python
metrics.counter(
    "taxi_request_transitions_total",
    labels={
        "transition": "assign_driver",
        "source_kind": "waiting",
        "target_kind": "en_route",
        "outcome": "success",
    },
)
```

Avoid high-cardinality labels such as request IDs, user IDs, timestamps, or free-form reasons.

## Derive Metrics from Domain Events When Possible

Because domain events are the authoritative record of business transitions, prefer deriving counters and histograms from the event stream rather than scattering metric calls through use cases. When immediate metrics are needed, emit them next to the event creation so the two stay in sync.

```python
event = driver_assigned_event(en_route, now)
metrics.counter(
    "taxi_request_domain_events_total",
    labels={"event_name": event.event_name},
)
```

## Log Failures with Explicit Error Context

For expected domain failures, log the error kind and the domain context, not stack traces or raw external payloads.

```python
match result:
    case Err(RequestNotFound(request_id=request_id)):
        logger.warning(
            "request not found",
            extra={"request_id": str(request_id), "error_kind": "request_not_found"},
        )
    case Err(InvalidState(current_kind=current_kind, expected_kind=expected_kind)):
        logger.warning(
            "invalid state for transition",
            extra={
                "current_kind": current_kind,
                "expected_kind": expected_kind,
                "error_kind": "invalid_state",
            },
        )
```

Unexpected infrastructure failures may still be logged with exception information, but keep domain failures specific.
