# CI Setup Checklist

Reference: [`../../kamae-py/references/ci-setup.md`](../../kamae-py/references/ci-setup.md).

## 10.1 Do required checks cover reviewer assumptions? - High

Flag CI that allows domain code to merge without the checks reviewers rely on: package validation, `uv run ruff format --check`, `uv run ruff check`, relevant mypy/pyright, relevant pytest, and policy checks when domain stance matters.

Downgrade when the repository is not a Python package or the changed files are documentation-only.

## 10.2 Are job matrices representative? - Medium

Flag workflows that test only the default environment when domain behavior, validation, persistence, or native code changes across Python versions, optional dependencies, database adapters, or deployment targets.

Do not require a huge matrix when local code paths are dependency-independent.

## 10.3 Are native/security jobs tied to actual risk? - Medium

Flag native-heavy, FFI, parser, or credential/PII-sensitive packages with no documented plan for fuzz/property tests, dependency audits, or secret scanning.

Do not require every optional safety job on every pull request. Scheduled, manual, or path-filtered jobs are acceptable when risk and cost are balanced.

## 10.4 Are advisory checks clearly advisory? - Low

Flag `continue-on-error`, ignored exit codes, or non-required checks that look mandatory in the workflow name or README.

Escalate when an advisory check is the only guard for native soundness, PII leakage, persistence integrity, or public API docs.

## 10.5 Can developers reproduce CI locally? - Low

Flag CI that has no documented local equivalent for the core checks, especially when failure output is hard to reproduce.

Suggest a short local command list or script that runs package validation, formatting, linting, type checking, and tests for touched code. Cross-check [`../../kamae-py/references/development-setup.md`](../../kamae-py/references/development-setup.md) for the recommended fast path and full pre-push loop.
