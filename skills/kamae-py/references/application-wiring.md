# Application Wiring and Ports

> **When to read:** Wiring use cases to repository ports, framework entrypoints, fakes, or deciding between explicit arguments and DI containers.
> **Related:** [`domain-modeling.md`](./domain-modeling.md), [`concurrency.md`](./concurrency.md), [`infrastructure-resilience.md`](./infrastructure-resilience.md).


## Default Stance: Explicit Arguments, Not a DI Container

Kamae Python prefers **plain function parameters** over Reader monads, service locators, or heavy DI frameworks.

```python
async def assign_driver_use_case(
    resolver: RequestResolver,
    store: RequestStore,
    authorizer: RequestAuthorizer,
    actor: Actor,
    request_id: UUID,
    driver_id: UUID,
    now: datetime,
) -> Result[EnRoute, AssignDriverError]:
    ...
```

Dependencies enter at the use-case boundary as typed ports. Pure transition functions stay free of infrastructure. Full orchestration example: [`state-transitions.md`](./state-transitions.md#keep-use-cases-thin).

Do not adopt a DI container for new code unless the repository already standardizes on one.

## Layer Responsibilities

| Layer | Responsibility | Depends on |
| --- | --- | --- |
| **Domain** | frozen models, value objects, pure transitions, error variants | stdlib, Pydantic |
| **Application** | async use cases, orchestration, authorization order | domain ports (`Protocol`) |
| **Infrastructure** | DB/HTTP/queue/SDK adapters implementing ports | framework, drivers |
| **Interface** | controllers, consumers, CLI, composition root | application + infrastructure |

Domain code must not import infrastructure packages.

## Ports and Adapters

**Ports** are `typing.Protocol` types that express what a use case needs. **Canonical** `RequestResolver` and `RequestStore` shapes: [`persistence-events.md`](./persistence-events.md#keep-repository-protocols-small). Introductory port concepts: [`domain-modeling.md`](./domain-modeling.md#define-repository-ports-with-protocols).

**Adapters** are concrete implementations in infrastructure modules.

```text
src/
  taxi_request/
    domain.py              # states, transitions, events, errors
    application.py         # use cases
    ports.py               # Protocol definitions (or beside use cases)
  infrastructure/
    postgres_request_store.py
    http_driver_directory.py
  api/
    routes.py              # composition root for HTTP
```

Keep port names narrow (`find_waiting`, `save_en_route`) rather than generic `get` / `update`.

## Composition Root

Wire dependencies only at framework entrypoints:

- FastAPI route modules and `Depends`
- ASGI lifespan startup
- Celery/RQ task factories
- CLI `main`

```python
def build_assign_driver_use_case(session: AsyncSession) -> AssignDriverUseCase:
    resolver = PostgresRequestResolver(session)
    store = PostgresRequestStore(session)
    authorizer = RequestAuthorizer(...)
    return partial(
        assign_driver_use_case,
        resolver=resolver,
        store=store,
        authorizer=authorizer,
    )
```

Framework-specific construction stays in `api/` or `infrastructure/`. Use cases remain plain functions or small callables that accept ports.

## What We Do Not Recommend

| Approach | Why not default |
| --- | --- |
| Reader / environment monad | Harder to read in Python; explicit args are enough |
| Global service registry | Hides dependencies and complicates tests |
| Injecting ORM models into use cases | Leaks persistence shape into application layer |
| `@inject` everywhere on domain code | Domain should stay framework-free |

If the project already uses FastAPI `Depends`, use it at the controller boundary to build use-case dependencies—not inside pure transitions.

## Testing With Fakes

Tests should pass in-memory or fake adapters through the same port types production uses. The fake implements the **canonical** port in [`persistence-events.md`](./persistence-events.md#keep-repository-protocols-small).

```python
class FakeRequestStore:
    def __init__(self) -> None:
        self.saved: list[tuple[EnRoute, tuple[DriverAssigned, ...]]] = []

    async def save_en_route(
        self,
        state: EnRoute,
        events: tuple[DriverAssigned, ...],
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> None:
        self.saved.append((state, events))
```

Use fakes for application tests. Use real database adapters for transaction, constraint, and locking tests.

Read [`infrastructure-resilience.md`](./infrastructure-resilience.md) when wrapping outbound HTTP, queue, or SDK calls with retry, timeout, or circuit-breaker policies.
