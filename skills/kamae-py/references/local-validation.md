# Local Validation Setup

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

Adjust `project.name`, `description`, and `[tool.mypy].files` before committing. For application repositories, `[tool.mypy].files` usually points at `src` and `tests`; for skill repositories, include `scripts`, examples, and tests.

## First-Time Setup

Use uv and Python 3.13.14:

```bash
uv python pin 3.13.14
uv sync
uv lock
```

If the project does not yet have a `pyproject.toml`, copy the bundled template first and then run:

```bash
uv sync
uv run python --version
uv run python -c "import pydantic; print(pydantic.__version__)"
```

## Local Check Loop

Run the same checks locally that CI will run:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy .
uv run pytest
```

For skill/plugin repositories, also run:

```bash
uv run python scripts/validate_package.py
```

## Pydantic Mypy Plugin

Keep the Pydantic v2 mypy plugin enabled in local validation:

```toml
[tool.mypy]
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

This catches model-construction mistakes, frozen-model mutation, untyped fields, `model_construct` mistakes, and dynamic alias problems before runtime.
