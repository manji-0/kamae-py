# Application Wiring Checklist

Reference: [`../../kamae-py/references/application-wiring.md`](../../kamae-py/references/application-wiring.md).

## 14.1 Are ports small and use-case shaped? - Medium

Flag repository or client protocols that mirror ORM tables, SDK surfaces, or framework handler signatures instead of the operations a use case actually needs.

## 14.2 Do use cases depend on ports, not concrete adapters? - High

Flag handlers, domain modules, or transition functions that call SQL, HTTP, queues, or SDK functions directly when a port and adapter split would isolate the workflow.

Do not flag composition-root wiring in `main`, bootstrap modules, or tests.

## 14.3 Is orchestration kept in use cases? - Medium

Flag business workflows spread across handlers, free functions, or repository adapters when a named use-case function or class should own load -> authorize -> transition -> persist ordering.

## 14.4 Are dependencies injected explicitly? - Low

Flag hidden globals, service locators, or new heavy DI containers introduced without project precedent. Prefer function parameters, struct fields, framework state, or composition root wiring.

Do not flag `Protocol` ports or existing framework dependency patterns when the project already uses them consistently.

## 14.5 Do tests swap ports instead of hitting real infrastructure? - Low

Flag use-case tests that require a live database or remote service when a fake port would exercise the workflow. Suggest in-memory or fake adapters for domain and use-case coverage.
