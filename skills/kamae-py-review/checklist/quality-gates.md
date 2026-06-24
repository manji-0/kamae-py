# Quality Gates Checklist

Reference: [`../../kamae-py/references/quality-gates.md`](../../kamae-py/references/quality-gates.md).

## 8.1 Is touched Python code formatted? - Low

Flag touched Python files that would fail `uv run ruff format --check`, unless they are generated or vendored code.

Formatting findings should stay Low unless poor formatting hides a risky domain, native, PII, persistence, or boundary change.

## 8.2 Are lint and type-check results clean for touched code? - Medium

Flag new Ruff warnings, mypy/pyright errors, or skipped quality gates when the repository normally runs them for the touched package.

Do not require a new global strict policy in a repo that does not use it. Instead, recommend running the existing local command and fixing warnings in touched code.

## 8.3 Are suppressions narrow and justified? - Medium

Flag broad `# type: ignore`, file-level `noqa`, module-level suppressions, or unexplained `# noqa: ...` around domain, boundary, PII, native, persistence, or error-handling code.

Downgrade for generated, vendored, or compatibility code when the source is documented and isolated.

## 8.4 Do suppressed checks hide domain safety risks? - High

Flag suppression or ignored warnings involving broad exceptions, unchecked `Any`, ignored awaitables, `assert` business checks, lossy casts, floating-point money/quantity comparisons, PII logging, or boundary deserialization.

Escalate when the suppression can admit invalid state, data loss, PII leakage, unsoundness, or missed persistence failure.

## 8.5 Are formatting/lint/type gates represented in CI or package validation? - Low

Flag packages with Python domain changes but no documented way to run formatting, linting, type checking, and tests. Suggest `uv run ruff format --check`, `uv run ruff check`, `uv run mypy`, and focused `uv run pytest`.

Do not block small documentation-only changes on missing Python CI.
