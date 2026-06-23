<!-- constrained-by ./local-validation.md -->
<!-- constrained-by ./ci-setup.md -->
<!-- derived-from ../scripts/apply_templates.py -->

# Development Environment Setup

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed and available on `PATH`.
- A Python version matching the project's range. This repository pins its local Python with [`.python-version`](../../../.python-version).

## Clone and Bootstrap

```bash
git clone <repository-url>
cd kamae-py
uv python install
uv sync
```

`uv python install` reads `.python-version` and installs the pinned patch release if it is not already present. `uv sync` creates the virtual environment and installs the locked dependencies.

## Verify the Installation

```bash
uv run python --version
uv run python -c "import pydantic; print(pydantic.__version__)"
uv run pytest
```

All tests should pass before you make changes.

## Run the Local Quality Gates

Use the same commands locally that CI runs:

```bash
uv run python scripts/validate_package.py
uv run python skills/kamae-py/scripts/check_kamae_policy.py --include-tests --strict
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest
```

Apply formatting with `uv run ruff format .` if `ruff format --check` fails.

## Working on the Skill Package

The skill lives under `skills/kamae-py/`:

- `SKILL.md` — the dispatching guide and frontmatter.
- `references/` — detailed reference documents.
- `scripts/` — helper scripts such as `apply_templates.py` and `check_kamae_policy.py`.
- `assets/templates/` — installable project templates.

When you add a new reference document, link to it from `SKILL.md` so the skill dispatcher surfaces it. Prefer relative links so `scripts/validate_package.py` can check them.

When you change `check_kamae_policy.py`, add or update tests in `tests/test_check_kamae_policy.py`.

## Apply Templates for Testing

`scripts/apply_templates.py` copies templates into a target directory. Use a temporary directory to test template changes without affecting this repository:

```bash
mkdir -p /tmp/kamae-test
uv run python skills/kamae-py/scripts/apply_templates.py --target /tmp/kamae-test --ci backend --force
```

Use `--dry-run` first when applying templates to an existing project.

## Dependency Changes

If you add or remove a dependency, update `uv.lock`:

```bash
uv add <package>
# or
uv remove <package>
uv lock
```

CI runs `uv sync --locked`, so a stale lockfile fails the build.

## Before Committing

1. Run the full local quality gate list above.
2. Review `git diff` for accidental template or lockfile changes.
3. Keep commits focused: one logical change per commit. For example, add the new reference document and its `SKILL.md` link in one commit; separate dependency updates into their own commit.

## Troubleshooting

- **Mypy reports missing `pydantic.mypy` plugin**: Ensure `[tool.mypy] plugins = ["pydantic.mypy"]` is set and the virtual environment is active through `uv run`.
- **Lockfile drift**: Run `uv lock` and commit the updated `uv.lock`.
- **Policy checker fails on a new reference**: The checker only inspects `src/` and `tests/` by default. Skill repositories are checked with `--include-tests`. If you added code elsewhere, add the path to `[tool.mypy].files` or run the checker with the appropriate scope.
