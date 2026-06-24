# Domain Modeling Checklist
Reference: [`../../kamae-py/references/domain-modeling.md`](../../kamae-py/references/domain-modeling.md).

## 1.1 Are semantic primitives represented as explicit types? - High

Flag bare `str`, `int`, `float`, `UUID`, or `dict` used directly for distinct domain concepts such as user IDs, order IDs, email addresses, money amounts, quantities, or external references.

Suggest small frozen Pydantic models, `NewType`, or validating constructors with `field_validator` / `model_validator`.

Do not flag primitives used as local temporaries, private adapter fields, test literals, serialization-only DTO fields, or values with no domain-specific invariant beyond the Python type.

## 1.2 Can callers bypass invariants? - High

Flag mutable domain models, public fields without validation, or `model_construct` / raw dict assembly that skips validators on invariant-bearing types.

Flag mutator methods or partial updates that change only one field of a multi-field invariant, skip revalidation, or allow invalid intermediate states to escape.

Do not flag construction inside the canonical constructor/adapter path, private test helpers, or DTO/row models converted through validating domain constructors before use.

## 1.3 Are states modeled explicitly with discriminated unions? - Medium

Flag a single Pydantic model with `status: str` plus many optional fields when separate frozen state variants with `kind: Literal[...]` would make required fields explicit.

Cross-check [`../../kamae-py/references/domain-modeling.md`](../../kamae-py/references/domain-modeling.md) for `Annotated[A | B, Field(discriminator="kind")]` patterns.

## 1.4 Are DTOs, ORM rows, and domain states separated? - Medium

Flag domain states carrying framework-only concerns, ORM mixins, or inbound deserialization settings that let external data bypass validation or couple invariants to storage shape.

Do not flag intentional read models, API response DTOs, or audited export types that cannot be deserialized back into domain state.

## 1.5 Is domain code organized by concept? - Low

Flag catch-all `models.py`, `types.py`, or `schemas.py` modules that aggregate unrelated concepts and separate behavior from data.

Do not flag cohesive modules with a narrow bounded-context purpose, generated schema modules, or compatibility shims kept intentionally thin.

## 1.6 Are money, time, and units explicit? - Medium

Flag amounts, quantities, durations, rates, and timestamps when code mixes units, currencies, time zones, or inclusive/exclusive ranges without types or named constructors.

## 1.7 Are domain states frozen and extra-forbid? - Medium

Flag mutable `BaseModel` domain states, missing `frozen=True`, or `extra="allow"` on lifecycle models unless the project documents a deliberate exception.
