# Pydantic Performance and Validation Cost

<!-- constrained-by ./domain-modeling.md -->
<!-- constrained-by ./boundary-defense.md -->

Kamae Python keeps Pydantic v2 as the default for domain states and boundary parsing. Validation has a real cost on large models, nested unions, and high-frequency endpoints. Treat performance as a boundary and hot-path concern—not a reason to weaken domain invariants.

## Where Cost Shows Up

| Hot spot | Typical cause | First response |
| --- | --- | --- |
| Request ingress | Parsing every HTTP body through nested models | Keep DTOs narrow; parse only fields the endpoint needs |
| DB rehydration | `validate_python` on every row in a list endpoint | Separate list/read DTOs from full aggregate states |
| Discriminated unions | `kind` dispatch + per-variant validation | One `TypeAdapter` per union; avoid re-parsing already-validated objects |
| Logging / metrics | `model_dump` on large states | Log identifiers and `kind` only; see [`loggable-identifiers.md`](./loggable-identifiers.md) |
| Tests | Re-validating identical fixtures | Build fixtures through constructors or cached adapters once per module |

`TypeAdapter` instances should be module-level constants. Pydantic caches validators; constructing a new adapter per request repeats schema compilation work.

```python
TaxiRequestAdapter = TypeAdapter(TaxiRequest)  # module scope


def request_from_row(row: Mapping[str, object]) -> TaxiRequest:
    return TaxiRequestAdapter.validate_python(row)
```

## When `model_construct` Is Acceptable

`model_construct` skips validation. Use it only on **trusted** paths where invariants were already enforced—typically inside a tested mapper after a prior Pydantic parse or a database driver that returned typed values.

```python
def waiting_from_row(dto: RequestRow) -> Waiting:
    # dto was validated by RequestRowAdapter; row columns match Waiting fields.
    return Waiting.model_construct(
        kind="waiting",
        request_id=dto.request_id,
        passenger_id=dto.passenger_id,
        created_at=dto.created_at,
    )
```

Do not use `model_construct` to skip validation on external HTTP, queue, or file input. Read [`boundary-defense.md`](./boundary-defense.md) and [`unsafe-boundaries.md`](./unsafe-boundaries.md) for the full policy.

Document every `model_construct` mapper with a short comment stating why the input is trusted and which invariant checks happen upstream.

## Reduce Work Without Bypassing Invariants

1. **Split models by use case.** A list view does not need the full aggregate union. Use a narrow read DTO at the repository port.
2. **Keep pure transitions cheap.** Transition functions receive already-validated domain states; they should not re-parse JSON or re-run Pydantic on every field.
3. **Prefer dataclasses for in-process-only helpers.** See the selection table in [`domain-modeling.md`](./domain-modeling.md). Do not duplicate the same concept in both Pydantic and dataclass without an explicit mapper.
4. **Avoid validators that perform I/O.** `@field_validator` and `@model_validator` run on every construction. Expensive checks belong in use cases or infrastructure adapters with explicit dependencies.
5. **Use `strict=True` at boundaries only.** Coercion (`"123"` → `123`) costs work and can hide data quality issues. Enable strict parsing on external DTOs, not on every internal handoff.

## Caching Strategies

| Strategy | Use when |
| --- | --- |
| Module-level `TypeAdapter` | Any repeated parse of the same schema |
| Frozen domain instances passed through layers | State already validated; transitions construct new frozen models |
| Read-model cache (Redis, in-process LRU) | Expensive aggregate assembly; cache **after** validation, keyed by version or ETag |
| `functools.lru_cache` on pure parse helpers | Small, immutable config or reference data parsed once per process |

Do not cache raw dicts from external systems and treat them as domain objects without re-validation on cache miss. Invalidation must be tied to aggregate version or TTL policy.

## msgspec and Other Fast Serializers

[msgspec](https://jcristharif.com/msgspec/) and similar libraries can outperform Pydantic on JSON encode/decode for simple, stable schemas. Kamae Python still prefers Pydantic for domain states and discriminated unions because of validator expressiveness, ecosystem integration, and mypy plugin support.

Acceptable pattern: **msgspec (or `orjson`) at the wire edge, Pydantic for domain.**

```text
HTTP bytes → msgspec.Struct (wire DTO) → map to Pydantic command/state → use case
```

Do not maintain two competing domain model systems. The msgspec struct is a transport shape; the Pydantic model remains the source of truth for invariants and transitions.

Compare options with benchmarks on **your** payload sizes and endpoint mix before switching. Micro-benchmarks on toy models rarely predict API gateway throughput.

## Profiling Checklist

Before replacing Pydantic on a hot path:

1. Profile with `py-spy` or `cProfile` on a realistic load test—not a single `validate_python` call in a notebook.
2. Confirm the bottleneck is validation, not N+1 queries, synchronous I/O on the event loop, or oversized `model_dump` in logging.
3. Apply the narrow-DTO and `model_construct` mapper patterns first.
4. Only then consider a faster serializer at the boundary while keeping Pydantic domain models.

Read [`concurrency.md`](./concurrency.md) when CPU-bound validation or transformation should move off the asyncio event loop.
