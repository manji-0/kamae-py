# Pydantic Performance Checklist

Reference: [`../../kamae-py/references/pydantic-performance.md`](../../kamae-py/references/pydantic-performance.md).

## 18.1 Is `model_construct` limited to trusted internal paths? - High

Flag `model_construct` used on boundary data, ORM rows, or partially trusted dicts when full validation is required.

Do not flag `model_construct` in hot paths that rehydrate already-validated internal state with a documented invariant.

## 18.2 Are high-frequency boundaries optimized intentionally? - Low

Flag expensive nested validation on hot endpoints without evidence that full validation is still applied where needed.

Suggest msgspec or narrower DTO adapters only when profiling or throughput requirements justify the tradeoff.

## 18.3 Do performance shortcuts preserve invariants? - High

Flag skipped validators, disabled config checks, or cached adapters that can admit extra fields, stale versions, or invalid discriminators into domain code.
