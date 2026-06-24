# Native and Unsafe Boundaries

> **When to read:** Touching `ctypes`, `cffi`, native extensions, `model_construct`, broad casts, unchecked bytes, or other code that bypasses Python/Pydantic invariants.
> **Related:** [`boundary-defense.md`](./boundary-defense.md), [`pydantic-performance.md`](./pydantic-performance.md), [`orm-adapters.md`](./orm-adapters.md).


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

## model_construct in ORM Mappers

<!-- constrained-by ./boundary-defense.md -->
<!-- constrained-by ./pydantic-performance.md -->

**Checklist mapping (7.2, 4.5):** `model_construct` skips validation. Use only when upstream already enforced invariants.

### Safe pattern: row DTO → domain state

The database driver or `RequestRow` adapter has already validated types and required fields. The mapper copies into a frozen domain model without re-running validators.

```python
RequestRowAdapter = TypeAdapter(RequestRow)


def waiting_from_row(row: Mapping[str, object]) -> Waiting:
    dto = RequestRowAdapter.validate_python(row)
    # SAFETY: dto validated; columns map 1:1 to Waiting; kind is constant for this query.
    return Waiting.model_construct(
        kind="waiting",
        request_id=dto.request_id,
        tenant_id=dto.tenant_id,
        passenger_id=dto.passenger_id,
        created_at=dto.created_at,
        version=dto.version,
    )
```

Requirements for every `model_construct` mapper:

1. **Document** with a `# SAFETY:` comment naming the upstream validator.
2. **Test** that invalid rows still fail at the DTO adapter, not at `model_construct`.
3. **Never** call `model_construct` on HTTP, queue, or file input.
4. **Keep field lists explicit**—do not splat `**dto.model_dump()` if extra DTO fields could pollute domain state.

### Unsafe pattern (do not use)

```python
# Bypasses validation on external input.
def waiting_from_api(data: dict[str, Any]) -> Waiting:
    return Waiting.model_construct(**data)
```

Read [`orm-adapters.md`](./orm-adapters.md) for full mapper layering between ORM entities, row DTOs, and domain states.

## ctypes: Memory and Error Handling

**Checklist mapping (7.3, 7.4):** Native calls belong in adapters with explicit lifetime and error mapping.

```python
import ctypes
from ctypes import c_int, c_void_p, POINTER


lib = ctypes.CDLL("libexample.so")
lib.example_process.argtypes = [c_void_p, c_int]
lib.example_process.restype = c_int


class NativeProcessError(Exception):
    def __init__(self, code: int) -> None:
        self.code = code


def process_buffer(data: bytes) -> int:
    if not data:
        raise ValueError("empty buffer")
    # copy=True: library must not retain pointer past call
    buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    code = lib.example_process(ctypes.cast(buf, c_void_p), len(data))
    if code != 0:
        raise NativeProcessError(code)
    return code
```

Practices:

- Set `argtypes` and `restype` on every exported function.
- Prefer `from_buffer_copy` unless the C API documents in-place mutation and lifetime rules.
- Never pass Python `bytes` directly if the C side stores the pointer asynchronously.
- Map non-zero return codes to typed exceptions; do not leak errno strings with customer data.
- Free native allocations in `try/finally` or use library-provided destroy functions.

```python
handle = lib.create_handle()
try:
  ...
finally:
    lib.destroy_handle(handle)
```

## cffi: ABI vs API Mode

| Mode | When to choose | Tradeoffs |
| --- | --- | --- |
| **ABI** (`ffi.dlopen`) | Vendor ships a stable `.so` / `.dll`; you have C headers | Fast to wire; relies on correct struct layouts and calling conventions |
| **API** (`ffi.set_source` + compile) | You control the C snippet or need speed / inline helpers | Build step in CI; clearer ownership; easier to audit |

**Choose ABI** when integrating third-party SDKs with documented headers and you want minimal build complexity.

**Choose API** when:

- The C surface is small and you can vendor a thin `.c` shim.
- You need `ffi.callback` with defined error propagation.
- ABI struct packing is fragile across platforms.

```python
# ABI example
import cffi

ffi = cffi.FFI()
ffi.cdef("""
    int parse_packet(const uint8_t *data, size_t len, struct Result *out);
""")
lib = ffi.dlopen("libpacket.so")


def parse_packet_safe(data: bytes) -> PacketDto:
    if len(data) > MAX_PACKET_SIZE:
        raise ValueError("packet too large")
    buf = ffi.from_buffer(data)
    out = ffi.new("struct Result *")
    rc = lib.parse_packet(buf, len(data), out)
    if rc != 0:
        raise PacketParseError(rc)
    return PacketDtoAdapter.validate_python({
        "kind": ffi.string(out.kind).decode(),
        "sequence": int(out.sequence),
    })
```

Always convert native output through a Pydantic DTO before domain models—same rule as HTTP boundaries.

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

```python
def test_process_buffer_rejects_empty() -> None:
    with pytest.raises(ValueError):
        process_buffer(b"")


def test_waiting_from_row_does_not_accept_missing_version() -> None:
    with pytest.raises(ValidationError):
        waiting_from_row({"request_id": str(uuid4()), "kind": "waiting"})
```
