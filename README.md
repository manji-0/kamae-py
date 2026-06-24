# kamae-py

Kamae Python is a Codex skill for robust server-side Python 3.12+ domain modeling with uv, Pydantic v2 discriminated unions, frozen state models, pure transition functions, boundary validation, and explicit domain errors.

Skills in this repository:

- `kamae-py` - generation guidance for Python backend domain models, use cases, state transitions, and boundary parsing.
- `kamae-py-review` - adversarial review checklists for Python domain diffs, with an optional `review_probe.py` router for changed paths.

## Install

Install the skill from this repository with your skill installer of choice, or copy `skills/kamae-py` into a Codex skills directory.

For Claude Code, add this repository as a marketplace and install the plugin:

```bash
/plugin marketplace add manji-0/kamae-py
/plugin install kamae-py@kamae-py
```

## Packaging

The package includes Claude, Codex, and Agents Marketplace manifests:

- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` describe the Claude plugin package.
- `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` describe the Codex plugin package and Agents Marketplace listing.
- `.codex-plugin/marketplace.json` lists skills for Codex marketplace installs.

Rules-based customization is documented in [`rules/README.md`](./rules/README.md). Override plugin defaults from `.claude/rules/` or `.codex/rules/` in your project, or from user-level rule directories.

## Development

This repository assumes uv and Python 3.12+ (currently pinned to `.python-version`).

```bash
uv python install
uv sync
uv run python skills/kamae-py/references/taxi-request.py
```

CI uses the same uv-backed checks:

```bash
uv run python scripts/validate_package.py
uv run python skills/kamae-py/scripts/check_kamae_policy.py --include-tests --strict
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest
```

Installable templates live under `skills/kamae-py/assets/templates/`. Use those copies when this skill is installed through `gh skill` or `npx skills`, because root-level files such as this repository's `pyproject.toml`, `.github/workflows/ci.yml`, and `scripts/` are not guaranteed to be installed with the skill.

The skill also includes `skills/kamae-py/scripts/apply_templates.py` to copy those templates into a target repository without overwriting existing files by default, and `skills/kamae-py/scripts/check_kamae_policy.py` to sanity-check a target project against the Kamae Python stance.

## Principles

- Model each domain state as a separate frozen Pydantic v2 model.
- Combine states with `Annotated[..., Field(discriminator="kind")]`.
- Parse external data with `TypeAdapter` at API, database, file, queue, and SDK boundaries.
- Express valid state transitions as pure functions.
- Keep expected business failures explicit and use-case-specific.
- Redact PII and secrets by default, including logs, metrics, errors, and events.
- Persist state changes and domain events atomically with idempotent retry paths.
- Exercise constructors, transitions, boundary parsing, redaction, and persistence edges in tests.
- Keep uv-run Ruff, mypy with the Pydantic v2 plugin, and pytest gates clean for touched domain code.

See `skills/kamae-py/SKILL.md` for the dispatching guide and `skills/kamae-py/references/` for detailed references.

## Customization

Rules live under `.claude/rules/`, `.codex/rules/`, user-level rule directories, or this repo's `rules/defaults/`. See [`rules/README.md`](./rules/README.md).

## Repository Layout

```text
skills/kamae-py/          Implementation guidance
skills/kamae-py-review/   Review procedure and checklist
rules/                    Project/user override format
```
