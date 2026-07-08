# CI Setup

> **Audience:** Projects installing the skill into their own repository. For the `kamae-py` skill repo itself, read [`development-setup.md`](./development-setup.md).
> **When to read:** Creating or updating GitHub Actions, branch protection guidance, or repository validation jobs.
> **Related:** [`quality-gates.md`](./quality-gates.md) (checks CI must run), [`local-validation.md`](./local-validation.md).


## Default GitHub Actions Workflow

CI should run the same checks as [`quality-gates.md`](./quality-gates.md). Use `uv sync --locked` so lockfile drift fails the build.

When this skill is installed, use the bundled templates under [`../assets/templates/`](../assets/templates/):

- [`../assets/templates/github-ci.yml`](../assets/templates/github-ci.yml) -> `.github/workflows/ci.yml` for ordinary Python backend repositories.
- [`../assets/templates/github-ci-skill-package.yml`](../assets/templates/github-ci-skill-package.yml) -> `.github/workflows/ci.yml` for skill/plugin repositories.
- [`../assets/templates/validate_package.py`](../assets/templates/validate_package.py) -> `scripts/validate_package.py` when using the skill-package workflow.

You can copy them with the bundled script:

```bash
python path/to/kamae-py/scripts/apply_templates.py --target . --ci backend
python path/to/kamae-py/scripts/apply_templates.py --target . --ci skill-package
```

The script is non-destructive by default; use `--dry-run` to preview and `--force` only when intentionally replacing files.

You can also add the Kamae policy check to CI:

```bash
python path/to/kamae-py/scripts/check_kamae_policy.py --target . --include-tests
```

Use `--strict` in CI to fail the build on warnings. For ordinary backend repositories, add it after `uv sync --locked`; for skill/plugin repositories, run it alongside `scripts/validate_package.py`.

If you opted out of installing the policy checker with `apply_templates.py --no-policy-checker`, remove the corresponding step from the generated workflow.

Recommended workflow for skill/plugin repositories:

```yaml
name: CI

on:
  pull_request:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  checks:
    name: Python 3.12+ checks
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
        with:
          enable-cache: true

      - name: Install Python
        run: uv python install

      - name: Sync dependencies
        run: uv sync --locked

      - name: Validate skill package
        run: uv run python scripts/validate_package.py

      - name: Check Kamae policy
        run: uv run python scripts/check_kamae_policy.py --include-tests --strict

      - name: Check formatting
        run: uv run ruff format --check .

      - name: Lint
        run: uv run ruff check .

      - name: Type check
        run: uv run pyrefly check .

      - name: Test
        run: uv run pytest
```

`uv python install` respects `.python-version`, so the job uses the same Python patch version as local development. `uv sync --locked` makes CI fail when `pyproject.toml` and `uv.lock` drift.

For ordinary backend repositories that are not skill packages, omit the `Validate skill package` step or use [`../assets/templates/github-ci.yml`](../assets/templates/github-ci.yml).

## What CI Should Protect

Keep these checks required for pull requests that touch domain, boundary, PII, persistence, event, test, or skill files:

- Package validation for plugin manifests, skill frontmatter, links, and Python syntax.
- Ruff formatting and linting.
- Pyrefly with built-in Pydantic v2 support.
- Pytest coverage for constructors, transitions, boundary parsing, redaction, persistence retries, and event compatibility.

## Pinning and Updates

Pin action majors or immutable SHAs according to the repository's security policy. For higher supply-chain assurance, pin third-party actions by full commit SHA and keep the version comment beside it.

Update action pins intentionally, not as drive-by churn in unrelated domain changes.

## Branch Protection

Require the CI job before merge. If a full test suite is too slow, split fast domain checks from slower integration tests, but keep the fast job required.

For backend services with adapters, add separate jobs for database-backed integration tests, migration checks, or outbox relay tests when those risks are in scope.
