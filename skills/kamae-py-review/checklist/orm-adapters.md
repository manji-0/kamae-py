# ORM Adapters Checklist

Reference: [`../../kamae-py/references/orm-adapters.md`](../../kamae-py/references/orm-adapters.md).

## 17.1 Are ORM entities kept out of domain modules? - High

Flag SQLAlchemy models, Django models, or session-bound entities imported by domain states, transitions, or use-case modules.

## 17.2 Do mappers validate on the way in and out? - High

Flag row-to-domain conversion that uses unchecked attribute access, `model_construct`, or `cast` instead of Pydantic adapters or explicit constructors.

## 17.3 Are sessions and transactions owned by adapters? - Medium

Flag use cases that manage ORM sessions directly when repository adapters should own persistence concerns.

## 17.4 Does lazy loading stay out of domain/use-case paths? - Medium

Flag implicit lazy loads, detached instances, or N+1 query patterns triggered during transition or use-case logic.

## 17.5 Are optimistic-lock columns mapped consistently? - High

Flag version/etag columns ignored on save, or ORM updates that can silently overwrite concurrent changes.

Cross-check [`aggregates.md`](./aggregates.md).
