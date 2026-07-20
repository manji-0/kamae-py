---
name: dependency-detection
description: Auto-detect Python dependencies from pyproject.toml
applies-to: "*"
type: library-preference
alwaysApply: false
---

# Dependency Detection

Read `pyproject.toml`, `.python-version`, and `uv.lock` during implementation and review. Load reference guides only when their dependency is present and relevant to the task.

Guide-backed detections:

- `pydantic` (v2) -> `references/domain-modeling.md`, `references/boundary-defense.md`, `references/state-transitions.md`, `references/library-guides/pydantic.md`
- `fastapi` -> `references/library-guides/fastapi.md`, `references/application-wiring.md`, `references/boundary-defense.md`
- `sqlalchemy` -> `references/orm-adapters.md`, `references/library-guides/sqlalchemy.md`
- `django` -> `references/orm-adapters.md`
- `hypothesis` -> `references/test-data.md`, `references/library-guides/hypothesis.md`
- `tenacity` -> `references/infrastructure-resilience.md`
- `opentelemetry-api` or `opentelemetry-sdk` -> `references/logging-metrics.md`
- `msgspec` -> `references/pydantic-performance.md`
- `orjson` -> `references/python-performance.md`, `references/pydantic-performance.md`
- `numpy` or `pandas` -> `references/python-performance.md`, `references/concurrency.md`
- `grpcio`, `protobuf`, `httpx`, `aiohttp` (cross-service clients) -> `references/service-boundaries.md`, `references/boundary-defense.md`
- `celery`, `kombu`, `aiokafka`, `redis` (queues / streams) -> `references/service-boundaries.md`, `references/stream-continuous-queries.md`, `references/persistence-events.md`

Detection-only dependencies:

- Package management: confirm uv usage from `[tool.uv]`, lockfile, or documented project convention
- Type checking: `pyrefly`, `mypy`, `pyright`; prefer pyrefly when `pydantic` is present because Pydantic v2 support is built in
- Lint/format: `ruff`
- Testing: `pytest`, `pytest-asyncio`
- Native/FFI: `cffi`, `ctypes` usage -> `references/unsafe-boundaries.md`
- Resilience helpers: `circuitbreaker`, `pybreaker`
- Settings/config: `pydantic-settings`, `python-dotenv`

Detection-only means the dependency should inform local code review or implementation context, but there is no dedicated plugin guide to load beyond the general topic references. Prefer existing project conventions and standard-library Python patterns before adding dependencies.

Library guides under `references/library-guides/` cover crate-specific defaults only. Prefer the matching topic guide under `references/` for full patterns.
