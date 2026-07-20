# Backend application package

This package represents the application layer of the backend.

## Suggested responsibilities

- api: HTTP routing, controllers, DTOs, dependency injection.
- core: configuration, logging, exceptions, middleware, auth, tracing.
- domain: entities, value objects, business rules, repository interfaces.
- infrastructure: database access, repositories, queue workers, external clients.
- modules: feature-specific implementations such as auth, users, transactions, uploads, reports.
- shared: reusable utilities, enums, constants, schemas.
