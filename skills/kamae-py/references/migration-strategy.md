# Migration Strategy

> **When to read:** Introducing Kamae Python into an existing class-based or ORM-centric codebase.
> **Related:** [`boundary-defense.md`](./boundary-defense.md), [`orm-adapters.md`](./orm-adapters.md), [`aggregates.md`](./aggregates.md).


Kamae Python describes an end state. Existing class-based services, blob models, and ORM-centric code can move toward it **incrementally** without a big-bang rewrite.

Default to the **Strangler Fig** pattern: new flows and high-risk areas first; leave stable legacy paths alone until touched.

## Principles

1. **Do not block product work on a full migration.**
2. **Improve boundaries before rewriting business rules.**
3. **Migrate one aggregate or workflow at a time.**
4. **Keep tests on the behavior users rely on.**
5. **Follow the repository's existing conventions when they do not weaken validation.**

## Phased Rollout

| Phase | Goal | Typical touch points | Risk |
| --- | --- | --- | --- |
| **0 — Baseline** | uv, Ruff, mypy, pytest on touched code | `pyproject.toml`, CI | Low |
| **1 — Boundary parsing** | Validate external data with Pydantic at edges | API DTOs, DB row models, queue payloads | Low |
| **2 — State shape** | Replace `status + Optional[...]` blobs with discriminated unions for new/changed flows | domain models for one workflow | Medium |
| **3 — Pure transitions** | Move rules out of service methods into named functions | application/domain modules | Medium |
| **4 — Ports/adapters** | Hide ORM/SDK behind `Protocol` ports | repositories, clients | Medium–high |
| **5 — Atomic persistence** | Save state + events together, add idempotency/versioning | repository adapters, outbox | High |
| **6 — Strict gates** | Expand mypy coverage, enable policy checker on migrated paths | CI, `files` config | Ongoing |

You do not need to finish one phase globally before starting the next locally. Within a single workflow, keep the phase order.

## Phase Details

### Phase 1: Boundary Parsing First

Lowest-risk win. Keep internal domain code as-is initially; stop unchecked data at the edges.

```python
RequestRowAdapter = TypeAdapter(RequestRow)

def row_to_waiting(row: Mapping[str, object]) -> Waiting:
    dto = RequestRowAdapter.validate_python(row)
    return Waiting(...)
```

### Phase 2: Introduce Discriminated Unions Beside Legacy Models

Do not delete the old `TaxiRequestService` class on day one.

```python
# New path
def assign_driver(waiting: Waiting, driver_id: UUID, now: datetime) -> EnRoute: ...

# Legacy wrapper during migration
class TaxiRequestService:
    def assign_driver(self, request_id: UUID, driver_id: UUID) -> None:
        row = self.repo.get(request_id)
        waiting = row_to_waiting(row)
        en_route = assign_driver(waiting, driver_id, datetime.now(UTC))
        self.repo.save(en_route.model_dump(mode="python"))
```

Delete the wrapper after callers move to the use case.

### Phase 3: Extract Use Cases

Turn service methods into async functions that accept ports. Full implementation: [`state-transitions.md`](./state-transitions.md#keep-use-cases-thin).

```python
async def assign_driver_use_case(
    resolver: RequestResolver,
    store: RequestStore,
    request_id: UUID,
    driver_id: UUID,
    now: datetime,
) -> Result[EnRoute, AssignDriverError]:
    ...
```

Controllers call the use case. Legacy services delegate to it until removed.

### Phase 4: Repository Protocols

Move SQLAlchemy/Django ORM queries into adapter modules. The use case should see only domain states and explicit errors.

Read [`orm-adapters.md`](./orm-adapters.md) for `mapped_column` entities, row DTOs, `domain_from_row_dto` mappers, and Django `select_for_update` write patterns.

### Phase 5: Events and Outbox

Add domain events only for workflows that need audit, integration, or async reactions. Start with one event type and one consumer.

## Coexistence Rules

While old and new styles coexist:

- **New code** follows Kamae Python for the workflow being changed.
- **Untouched legacy code** is not required to migrate immediately.
- **Do not mix** blob state models and discriminated unions as competing sources of truth for the same aggregate.
- **Document** temporary wrappers with a short comment and remove them in the same epic when possible.

## Incremental Type Safety

Expand mypy coverage gradually:

```toml
[tool.mypy]
files = [
    "src/taxi_request",
    "tests/taxi_request",
]
```

Add directories as they migrate. Use `check_kamae_policy.py` on migrated packages before enabling `--strict` globally.

## What Not to Do

- Rewrite every model before shipping one vertical slice
- Introduce a DI framework solely for migration aesthetics
- Force `Result` into every legacy method before boundaries are typed
- Block releases on full outbox/event infrastructure if the workflow still needs only CRUD

## Success Criteria for One Migrated Workflow

- External inputs parsed with Pydantic at the boundary
- Aggregate state represented as a frozen discriminated union
- Business transitions are pure functions with tests
- Use case returns explicit errors or maps infrastructure failures clearly
- Repository adapter persists state atomically where required
- Observability follows [`loggable-identifiers.md`](./loggable-identifiers.md)

Read [`aggregates.md`](./aggregates.md) and [`application-wiring.md`](./application-wiring.md) when choosing the first workflow to migrate.
