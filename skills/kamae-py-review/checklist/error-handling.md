# Error Handling Checklist
Reference: [`../../kamae-py/references/error-handling.md`](../../kamae-py/references/error-handling.md).

## 3.1 Are business failures explicit instead of hidden exceptions? - High

Flag broad `except Exception`, swallowed failures, or infrastructure exceptions leaking through use-case APIs when the project uses explicit domain error enums or Result values.

Do not flag framework boundaries, startup/configuration failures, or test/fixture exceptions when they are clearly isolated.

## 3.2 Is `assert` avoided for runtime business validation? - High

Flag `assert` guarding business preconditions in production code. Suggest explicit errors or validators instead.

## 3.3 Are domain errors specific and use-case shaped? - Medium

Flag `Exception`, bare `ValueError`, `RuntimeError`, or opaque string errors returned from domain constructors and use cases when callers need to branch.

## 3.4 Are infrastructure errors converted intentionally? - Medium

Flag leaking SQLAlchemy/Django/HTTP client exceptions, raw DB driver errors, or config errors directly through public domain/use-case APIs.

## 3.5 Are async use cases layered correctly? - Medium

Cross-check [`../../kamae-py/references/error-handling.md`](../../kamae-py/references/error-handling.md). Flag async domain transitions that perform I/O, or infrastructure error types leaking through `async def` boundaries without mapping.

## 3.6 Are locks or blocking work held across await points? - High

Flag mutex guards, database row locks, blocking ORM/session usage, or other exclusive resources held across `await` in use cases or adapters unless the project explicitly designs for it.

Cross-check [`concurrency.md`](./concurrency.md).

## 3.7 Are error variants meaningful to callers? - Low

Flag vague variants such as `other: str` or `invalid_input: str` when callers need to branch exhaustively.

## 3.8 Are exception chains preserved with `raise ... from`? - Medium

Cross-check [`../../kamae-py/references/error-handling.md`](../../kamae-py/references/error-handling.md). Flag use-case errors that stringify inner failures with f-strings instead of preserving exception chains for logs.

## 3.9 Do error messages avoid PII and secrets? - High

Cross-check [`pii-protection.md`](./pii-protection.md). Flag error text that embeds email, phone, tokens, or raw SQL/HTTP bodies.
