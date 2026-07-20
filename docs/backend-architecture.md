# Backend Architecture Blueprint

This repository is being structured as a monorepo with a clear separation between backend and frontend.

## Architectural goals

- Backend-first, modular, and scalable.
- Strong validation at every boundary.
- Domain logic isolated from infrastructure details.
- Cross-cutting concerns implemented once and reused globally.
- Environment configuration validated at startup.
- Unit and integration tests for every module.

## Core principles

1. Validation pipeline
   - Request DTOs and response DTOs live near the API layer.
   - Domain objects validate their own invariants.
   - Infrastructure boundaries validate external data.

2. Domain/infrastructure separation
   - Domain services contain business rules.
   - Repositories and adapters implement persistence and external integrations.
   - The domain depends on interfaces, not concrete ORM or database implementations.

3. Cross-cutting concerns
   - Logging, exception handling, auth, tracing, security, caching, background jobs, and settings live in core modules.
   - They are applied globally through middleware, dependency injection, and shared utilities.

4. Environment validation
   - Settings are loaded through a strict configuration schema.
   - Invalid or missing environment variables fail fast at startup.

5. Testing strategy
   - Unit tests target domain services and validators.
   - Integration tests target API endpoints, database interactions, and workers.

## Proposed structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── deps/
│   │   ├── v1/
│   │   │   ├── routers/
│   │   │   └── dto/
│   │   │       ├── request/
│   │   │       └── response/
│   ├── core/
│   │   ├── config/
│   │   ├── exceptions/
│   │   ├── logging/
│   │   ├── middleware/
│   │   ├── security/
│   │   └── dependency_injection/
│   ├── domain/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── services/
│   │   └── ports/
│   ├── infrastructure/
│   │   ├── db/
│   │   ├── repositories/
│   │   ├── external_clients/
│   │   ├── cache/
│   │   └── workers/
│   ├── modules/
│   │   ├── auth/
│   │   ├── users/
│   │   ├── transactions/
│   │   ├── uploads/
│   │   └── reports/
│   ├── shared/
│   │   ├── schemas/
│   │   ├── enums/
│   │   ├── constants/
│   │   └── utils/
│   └── main.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── factories/
├── alembic/
├── requirements.txt
├── pyproject.toml
└── .env.example

frontend/
├── src/
│   ├── app/
│   ├── features/
│   ├── shared/
│   ├── services/
│   └── types/
├── public/
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## How each requirement is implemented

- Validation pipeline: API DTOs in api/v1/dto, domain validation in domain/services and entities, global validators in core.
- Domain/infrastructure separation: domain layers use repository interfaces in domain/ports; infrastructure implements them in infrastructure/repositories.
- Cross-cutting concerns: logging, exceptions, middleware, security, config, and dependency injection live under core.
- Environment validation: configuration schema under core/config and loaded early in app startup.
- Testing: unit tests for domain logic, integration tests for routers, repositories, and workers.
