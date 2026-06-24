# Unsafe Boundaries Checklist

Reference: [`../../kamae-py/references/unsafe-boundaries.md`](../../kamae-py/references/unsafe-boundaries.md).

## 7.1 Is unchecked/native code absent from domain logic? - High

Flag `ctypes`, `cffi`, native extension calls, unchecked buffer handling, `model_construct`, broad `cast`, or raw `bytes` parsing inside domain entities, value objects, state transitions, use cases, DTO conversion, PII wrappers, or repository protocols.

Do not flag native code isolated in adapter/infrastructure modules when it is hidden behind a safe API and does not bypass domain constructors, validation, authorization, or redaction.

## 7.2 Is native access contained behind a safe abstraction? - High

Flag public APIs that require callers to uphold undocumented aliasing, lifetime, FFI, or ownership preconditions. Prefer a safe function that validates inputs before calling native code.

Document caller obligations in docstrings when a wrapper cannot fully validate preconditions.

## 7.3 Are safety invariants documented at the native site? - Medium

Flag native or unchecked blocks without a nearby comment explaining the invariant, where it is established, and why aliasing, lifetimes, initialization, alignment, and bounds are valid.

Do not accept comments that merely restate the operation.

## 7.4 Can native code bypass domain construction or redaction? - High

Flag native code that constructs domain values from raw data without the normal adapter/constructor path, or that exposes PII/secrets through logs, `repr`, exceptions, FFI callbacks, metrics labels, or raw buffers.

## 7.5 Are native boundaries tested with appropriate tools? - Medium

Flag native wrappers without focused tests for normal inputs, boundary inputs, rejected constructors, mutation paths, invalid handles, or error paths.

Suggest fuzzing or property tests when the native block owns memory, pointer aliasing, initialization, or FFI lifetime contracts. Do not require those tools for every small safe-domain change.
