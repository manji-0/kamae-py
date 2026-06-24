# Quality Gates

> **When to read:** Before finishing changes to domain, boundary, PII, persistence, tests, or sample code. **Canonical command list** for local and CI checks.
> **Related:** [`local-validation.md`](./local-validation.md), [`ci-setup.md`](./ci-setup.md), [`development-setup.md`](./development-setup.md).

## Baseline Commands

Use uv to run project tools. Prefer the repository's existing commands when present; otherwise use these defaults for touched Python code:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy .
uv run pytest
```

For narrow changes, run the smallest command set that covers the touched files and state the limitation.

For first-time local setup, read [`local-validation.md`](./local-validation.md) and copy or merge templates from [`../assets/templates/`](../assets/templates/). Installed skills include files under the skill directory, but do not reliably install this repository's root `pyproject.toml`, `uv.lock`, `.github/`, or `scripts/`.

## Skill-Package and Policy Checks

Skill/plugin repositories should also run:

```bash
uv run python scripts/validate_package.py
uv run python path/to/kamae-py/scripts/check_kamae_policy.py --include-tests --strict
```

In the **kamae-py** repository itself, use `skills/kamae-py/scripts/check_kamae_policy.py`. Use `ruff format --check` in CI; apply with `ruff format .` locally when the check fails. See [`ci-setup.md`](./ci-setup.md) for workflow wiring and [`development-setup.md`](./development-setup.md) for this repo's dev workflow.

## Ruff Signals That Matter for Domain Safety

Formatting keeps diffs reviewable so domain, boundary, PII, native, and persistence changes are easier to inspect.

Pay special attention to patterns that can hide invalid states or operational failures:

- Broad `except Exception`, swallowed exceptions, or ignored awaitables.
- `print`, raw logging of Pydantic models, or string formatting of sensitive values.
- `assert` used for runtime business validation.
- Mutable defaults, global mutable state, and implicit time/randomness in transitions.
- Unchecked `Any`, broad `dict`, `type: ignore`, and `cast` near domain boundaries.
- Floating-point money, lossy casts, or unit-less quantities.

Do not require every lint to be globally enabled. Use them as review signals when they appear in touched code or local configuration.

## Type Checking

Run mypy or pyright when the project has either configured. For Pydantic v2 projects, prefer mypy with `plugins = ["pydantic.mypy"]` and strict plugin flags (`init_forbid_extra`, `init_typed`, `warn_required_dynamic_aliases`). Full `[tool.mypy]` and `[tool.pydantic-mypy]` example: [`domain-modeling.md`](./domain-modeling.md#configure-mypy-with-the-pydantic-plugin).

The plugin catches Pydantic-specific risks that plain mypy can miss: untyped model fields, frozen-model mutation, mistyped `model_construct`, invalid field defaults, extra constructor keywords, and required dynamic aliases.

Avoid weakening type checks around discriminated unions, repository protocols, result values, boundary DTOs, or Pydantic model construction.

If a suppression is necessary, keep it narrow and explain why the runtime validation or adapter contract still preserves the invariant.

## Tests

Run focused pytest tests for domain constructors, transitions, DTO conversion, PII redaction, native wrappers, repository transactions, outbox behavior, and retry/idempotency paths.

Generated, vendored, or externally maintained code can be exempt from the full lint bar, but safe wrappers around it still follow boundary validation, PII, and native-boundary guidance.
