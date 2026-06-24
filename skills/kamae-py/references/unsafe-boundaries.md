# Native and Unsafe Boundaries

> **When to read:** Touching `ctypes`, `cffi`, native extensions, `model_construct`, broad casts, unchecked bytes, or other code that bypasses Python/Pydantic invariants.
> **Related:** [`boundary-defense.md`](./boundary-defense.md), [`pydantic-performance.md`](./pydantic-performance.md).


## Default Stance

Keep unchecked operations out of domain logic. Domain models, value objects, state transitions, use cases, DTO conversion, PII redaction, and repository protocols should not use native pointer APIs or bypass Pydantic validation.

Treat these as unsafe-equivalent boundaries in Python:

- `ctypes`, `cffi`, C extensions, native SDK handles, memory views, and binary protocol parsers.
- Generated bindings and codegen clients with broad or inaccurate types.
- `BaseModel.model_construct`, `typing.cast`, `Any`, `# type: ignore`, unchecked indexing, and broad `dict` access used to bypass validation.
- Pickle, dynamic imports, `eval`, `exec`, or deserialization formats that can execute code.

## Contain Behind Safe APIs

Place unchecked code in adapter or infrastructure modules. Expose a small safe API that validates every precondition before returning domain values.

```python
class NonEmptyBytes(DomainModel):
    value: bytes

    @classmethod
    def parse(cls, value: bytes) -> "NonEmptyBytes":
        if not value:
            raise ValueError("bytes must be non-empty")
        return cls(value=value)


def first_byte(raw: bytes) -> int:
    data = NonEmptyBytes.parse(raw)
    return data.value[0]
```

Do not use unchecked code to bypass tenant checks, constructors, Pydantic adapters, redaction wrappers, or error mapping.

## Document Safety Invariants

Every native-wrapper function or unchecked construction path should explain:

- What invariant makes the operation safe.
- Where that invariant is established.
- Which invalid inputs are rejected.
- How PII and secrets are prevented from leaking through logs, errors, callbacks, metrics, or memory dumps.

Prefer a docstring or nearby `# SAFETY:` comment when the code performs something the type checker and Pydantic cannot verify.

## Test the Wrapper

For native or unchecked boundary changes, add focused tests around the safe wrapper: normal inputs, boundary inputs, rejection paths, null/invalid handles, error paths, redaction, and mutation paths that preserve invariants.

For binary parsers or native-heavy adapters, consider property tests, fuzzing, sanitizer-enabled builds, or vendor-provided test suites. Do not require these for every domain change, but recommend them when memory, pointer lifetime, or binary compatibility is the core risk.
