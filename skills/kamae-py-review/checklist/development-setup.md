# Development Setup Checklist

Reference: [`../../kamae-py/references/development-setup.md`](../../kamae-py/references/development-setup.md).

## 11.1 Is domain code free of framework and ORM imports? - High

Flag `domain` modules that import FastAPI, Django models, SQLAlchemy sessions, boto3, or other infrastructure crates when the team claims a Kamae-style split.

## 11.2 Can domain and use-case tests run without Docker? - Medium

Flag workflows where basic transition or use-case tests require live databases or external services when fake ports would suffice.

## 11.3 Are fixtures built through constructors? - Medium

Cross-check [`tests.md`](./tests.md). Flag test helpers that bypass invariants with raw dicts, `model_construct`, or ORM rows in domain/use-case tests.

## 11.4 Is a documented local check loop available? - Low

Flag projects adopting Kamae conventions without a fast path and full pre-push command list aligned with [`ci-setup.md`](../../kamae-py/references/ci-setup.md).

## 11.5 Are secrets and PII kept out of committed env files? - High

Cross-check [`pii-protection.md`](./pii-protection.md). Flag committed `.env` files, real credentials in examples, or local setup docs that encourage logging raw PII for debugging.

## 11.6 Does test layout match layer boundaries? - Medium

Flag domain tests that pull in HTTP servers or DB pools directly instead of testing through fakes at the use-case layer or adapters at the infrastructure layer.
