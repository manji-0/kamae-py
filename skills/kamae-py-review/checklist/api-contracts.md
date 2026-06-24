# API Contracts Checklist

Reference: [`../../kamae-py/references/api-contracts.md`](../../kamae-py/references/api-contracts.md).

## 9.1 Do public domain APIs document their contract? - Medium

Flag public domain types, constructors, state models, transition functions, repository protocols, DTO conversions, and adapter wrappers whose docstrings omit important invariants, valid inputs, units, lifecycle rules, side effects, or consistency guarantees.

Do not require docstrings on private helpers unless they encode a subtle invariant that reviewers or maintainers are likely to misuse.

## 9.2 Are errors, exceptions, and native contracts documented? - High

Flag public functions returning domain errors or Result values when docs hide important variants callers must handle. Flag production exceptions without documenting which layer catches them.

Native wrappers must document safe API guarantees and caller obligations.

## 9.3 Do examples show the safe path? - Medium

Flag examples that construct invariant-bearing values through `model_construct`, bypass DTO conversion, ignore validation errors without explanation, leak PII, or show impossible state transitions.

Prefer examples that run under doctest or project snippet tests when the repository uses them.

## 9.4 Are docstrings and examples maintained? - Low

Flag stale type names, examples that no longer run, or docs that contradict current constructor/error/state behavior.

Escalate when stale docs can cause callers to bypass validation, mishandle an error variant, misuse native code, or leak sensitive data.

## 9.5 Are documentation checks scoped appropriately? - Low

Flag public library packages that lack any way to catch broken examples or API drift.

Do not require docstrings on every private helper in application code unless the project already has that policy. Safe wrappers around generated code still need contract docs.
