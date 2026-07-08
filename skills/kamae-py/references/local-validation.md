# Local Validation Setup

> **Audience:** Projects bootstrapping from skill templates (`gh skill`, `npx skills`). For this repository's dev workflow, read [`development-setup.md`](./development-setup.md).
> **When to read:** Bootstrapping local `pyproject.toml`, `.gitignore`, pyrefly/Pydantic settings, Ruff, pytest, or skill-package validation.
> **Related:** [`quality-gates.md`](./quality-gates.md) (canonical check commands), [`ci-setup.md`](./ci-setup.md).


## Use the Bundled Templates

When this skill is installed with `gh skill` or `npx skills`, repository-root files such as `pyproject.toml`, `.github/workflows/ci.yml`, and `scripts/validate_package.py` are not installed with it. Use the templates under [`../assets/templates/`](../assets/templates/) when bootstrapping a project.

The quickest path is the bundled script:

```bash
python path/to/kamae-py/scripts/apply_templates.py --target . --ci backend
```

For skill/plugin repositories:

```bash
python path/to/kamae-py/scripts/apply_templates.py --target . --ci skill-package
```

The script does not overwrite existing files unless `--force` is set. Use `--dry-run` first when applying it to an existing repository.

## Policy Sanity Check

After bootstrapping, run the bundled policy checker to catch common Kamae stance issues before they reach CI:

```bash
python path/to/kamae-py/scripts/check_kamae_policy.py --target .
```

Add `--include-tests` to also scan `tests/`. Use `--strict` to treat warnings as errors. The checker covers project configuration, forbidden package-manager files, frozen domain models, `kind` discriminated unions, pure transitions, and a few risky patterns such as broad `except` and `typing.cast`.

Recommended local files:

- [`../assets/templates/pyproject.toml`](../assets/templates/pyproject.toml) -> `pyproject.toml` or merge into the existing file.
- [`../assets/templates/gitignore`](../assets/templates/gitignore) -> `.gitignore` or merge into the existing file.
- [`../assets/templates/validate_package.py`](../assets/templates/validate_package.py) -> `scripts/validate_package.py` for skill/plugin repositories only.

Adjust `project.name`, `description`, and `[tool.pyrefly].project-includes` before committing. For application repositories, `project-includes` usually points at `src` and `tests`; for skill repositories, include `scripts`, examples, and tests.

## First-Time Setup

Use uv and Python 3.12+. **Docker is optional**—the default path is a local Python toolchain plus optional containerized dependencies only when you need them (for example Postgres integration tests).

### 1. Install uv and pin Python

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # or brew install uv
cd your-project
uv python pin 3.13
```

### 2. Bootstrap from templates (new projects)

```bash
python path/to/kamae-py/scripts/apply_templates.py --target . --ci backend --dry-run
python path/to/kamae-py/scripts/apply_templates.py --target . --ci backend
```

### 3. Sync dependencies

```bash
uv sync
uv lock
uv run python --version
uv run python -c "import pydantic; print(pydantic.__version__)"
```

If the project does not yet have a `pyproject.toml`, copy the bundled template first, then run `uv sync`.

### 4. Local services without Docker (optional)

When integration tests need Postgres or Redis:

| Service | macOS (Homebrew) | Linux (apt) |
| --- | --- | --- |
| PostgreSQL | `brew install postgresql@16 && brew services start postgresql@16` | `sudo apt install postgresql` |
| Redis | `brew install redis && brew services start redis` | `sudo apt install redis-server` |

Create a dev database and point settings at it:

```bash
createdb myapp_dev
export DB_HOST=localhost DB_PORT=5432 DB_NAME=myapp_dev DB_USER=$USER DB_PASSWORD=
```

Use `.env` with pydantic-settings (see [`boundary-defense.md`](./boundary-defense.md#environment-and-cli-boundaries)). Add `.env` to `.gitignore`.

### 5. Verify the toolchain

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyrefly check .
uv run pytest
python path/to/kamae-py/scripts/check_kamae_policy.py --target . --include-tests
```

### 6. Editor integration

- Enable Ruff as the format/lint provider in the IDE.
- Set the interpreter to `.venv/bin/python` after `uv sync`.
- Run `uv run pyrefly check` from the project root so built-in Pydantic support resolves.

## Local Check Loop

After bootstrap, run the baseline commands in [`quality-gates.md`](./quality-gates.md). For skill/plugin repositories, also run `uv run python scripts/validate_package.py`.

Install pre-commit hooks from [`quality-gates.md`](./quality-gates.md#pre-commit-integration) when the team wants automatic formatting before commit.

For pyrefly and Pydantic settings, merge [`../assets/templates/pyproject.toml`](../assets/templates/pyproject.toml) or follow [`domain-modeling.md`](./domain-modeling.md#configure-pyrefly-for-pydantic-models).

## When to Add Docker

Use Docker or Compose when:

- Production parity requires exact image versions.
- Onboarding must not install Postgres/Redis locally.
- CI uses the same `docker compose up` for integration tests.

Keep domain unit tests runnable with `uv run pytest` and no containers. Put integration tests behind a marker (`pytest -m integration`) or optional compose profile.
