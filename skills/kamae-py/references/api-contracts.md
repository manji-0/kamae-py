# API Contracts and Docstrings

> **When to read:** Documenting public domain APIs, repository protocols, transition functions, DTO conversion, event schemas, or safe wrappers.
> **Related:** [`domain-modeling.md`](./domain-modeling.md), [`state-transitions.md`](./state-transitions.md), [`unsafe-boundaries.md`](./unsafe-boundaries.md).


## Document Domain Contracts, Not Narration

Public domain APIs should explain what callers may rely on: invariants, construction paths, state transitions, errors, side effects, transaction expectations, idempotency, redaction, and unsafe/native boundary contracts.

Private helpers usually do not need docstrings unless they encode a subtle invariant.

## What to Document

Document these public items when they are part of a domain or adapter contract:

- Value objects: meaning, validation rules, units, ranges, privacy/redaction expectations.
- Constructors and parsers: accepted inputs, rejected inputs, and error variants.
- State models and discriminated unions: valid lifecycle states and when each variant is produced.
- Transition functions: source state, target state, preconditions, emitted events, and failure modes.
- Repository protocols: transaction boundaries, consistency guarantees, optimistic locking, idempotency, and error mapping.
- DTO and row conversion functions: external shape assumptions and validation boundaries.
- Native wrappers: safe API guarantees and caller obligations.

Avoid docstrings that merely repeat the function name.

```python
def assign_driver(waiting: Waiting, driver_id: UUID, now: datetime) -> EnRoute:
    """Move a waiting request to en-route after caller has authorized assignment.

    The transition is pure: it does not persist state, publish events, or read time.
    The caller is responsible for saving the returned state with a matching
    `DriverAssigned` event in one transaction.
    """
```

## Use Structured Sections When Useful

Use short headings such as `Raises`, `Returns`, `Side effects`, `Transaction`, `Idempotency`, `Redaction`, or `Safety` only when they add concrete contract value. Do not add empty boilerplate sections.

For functions returning Result values, describe the error variants callers must handle. For functions that can raise framework or Pydantic exceptions, state which layer catches them.

## Examples

Examples should demonstrate the safe construction path, not raw-field shortcuts. Use synthetic IDs and fake personal data. Never include real secrets, tokens, emails, customer IDs, production payloads, or private URLs in docs.

When a type redacts `repr`, logs, or serialization, mention that as part of the public contract.
