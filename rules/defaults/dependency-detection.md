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

- `pydantic` (v2) -> `references/domain-modeling.md`, `references/boundary-defense.md`, `references/state-transitions.md`
- `sqlalchemy` -> `references/orm-adapters.md`
- `django` -> `references/orm-adapters.md`
- `hypothesis` -> `references/test-data.md`
- `tenacity` -> `references/infrastructure-resilience.md`
- `opentelemetry-api` or `opentelemetry-sdk` -> `references/logging-metrics.md`
- `msgspec` -> `references/pydantic-performance.md`

Detection-only dependencies:

- Package management: confirm uv usage from `[tool.uv]`, lockfile, or documented project convention
- Type checking: `pyrefly`, `mypy`, `pyright`; prefer pyrefly when `pydantic` is present because Pydantic v2 support is built in
- Lint/format: `ruff`
- Testing: `pytest`, `pytest-asyncio`
- Async HTTP/clients: `httpx`, `aiohttp`
- Messaging/queues: `celery`, `kombu`, `aiokafka`, `redis`
- Native/FFI: `cffi`, `ctypes` usage -> `references/unsafe-boundaries.md`
- Resilience helpers: `circuitbreaker`, `pybreaker`
- Settings/config: `pydantic-settings`, `python-dotenv`

Detection-only means the dependency should inform local code review or implementation context, but there is no dedicated plugin guide to load beyond the general topic references. Prefer existing project conventions and standard-library Python patterns before adding dependencies.
