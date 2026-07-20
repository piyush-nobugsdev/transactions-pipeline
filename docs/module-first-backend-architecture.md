# Module-first backend architecture

This repository should follow a module-first structure, where each business capability owns its own controllers, application layer, domain layer, infrastructure layer, tests, and docs.

## Key difference from a global layered layout

A global layered layout puts files like api, domain, and infrastructure at the top level and then spreads features across them.

A module-first layout keeps the feature boundary intact:

- core contains shared infrastructure and cross-cutting concerns
- modules contain feature ownership and business logic
- each module can evolve independently

## Recommended structure

```text
backend/
  app/
    main.py
    core/
      config/
      dependencies/
      exceptions/
      logging/
      middleware/
      security/
      utils/
    modules/
      auth/
      users/
      transactions/
      uploads/
      reports/
```

## Module contract

Each module should follow this shape:

```text
modules/<module>/
  <module>.module.py
  controllers/
  application/
    dto/
      request/
      response/
    commands/
    queries/
    services/
    mappers/
  domain/
    entities/
    value_objects/
    repositories/
    services/
  infrastructure/
    persistence/
    external/
    mappers/
  docs/
  tests/
```

## About app/api/deps

In a FastAPI-based implementation, the equivalent of shared dependency helpers lives in core/dependencies or a shared app dependency module.

It should contain reusable FastAPI dependencies such as:

- get_current_user
- get_db_session
- require_admin
- pagination_params
- request-scoped services

It should not contain route implementations or module-specific DTOs.
