# Boundary Defense Checklist
Reference: [`../../kamae-py/references/boundary-defense.md`](../../kamae-py/references/boundary-defense.md).

## 4.1 Is every external boundary converted through DTO -> domain? - High

Flag HTTP handlers, queue consumers, DB row mappers, file/config/env readers, or CLI parsers that pass raw data directly into domain logic without validated conversion.

Do not flag raw DTO/read-model construction when the value stays in the adapter layer, or direct domain construction inside a validating adapter/constructor path.

## 4.2 Is Pydantic treated as the only boundary validator? - High

Flag code that relies on `model_validate` alone for domain invariants such as non-empty strings, valid IDs, positive amounts, ranges, or cross-field rules when a domain constructor or transition precondition is still required.

## 4.3 Are domain states over-configured for external formats? - Medium

Flag inbound `extra="allow"`, permissive alias settings, or ORM/session coupling on domain states when separate DTOs/rows would protect invariants or redaction.

Do not flag intentional read models, projections, or response-only DTOs.

## 4.4 Are DTO defaults and unknown fields intentional? - Medium

Flag inbound DTOs using broad defaults, optional fields, or permissive unknown-field handling when missing or misspelled input could change business meaning. Prefer explicit defaults and `extra="forbid"` when compatibility does not require permissiveness.

## 4.5 Are unchecked casts and `Any` avoided at boundaries? - High

Flag `typing.cast`, `# type: ignore`, unchecked `dict[str, Any]`, `model_construct`, or subscript access on unknown payloads used to create trusted domain objects.

## 4.6 Are authorization and tenant boundaries checked? - High

Flag handlers or use cases that trust path/body tenant IDs, actor IDs, or ownership claims without comparing them to authenticated context before domain operations.
