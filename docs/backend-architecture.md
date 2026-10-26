# Backend Architecture

This document describes the architecture implemented in the repository. The
backend development requirements and mandatory conventions are in
[AGENTS.md](../AGENTS.md); this guide records the current code organization.

## System shape

The backend uses FastAPI, with shared infrastructure in `backend/app/core/` and
vertical business capabilities in `backend/app/modules/`. SQLAlchemy persistence
models and shared DB session infrastructure currently live outside individual
modules; modules access persistence through adapters and repository contracts.

```text
FastAPI controllers
        |
        v
Application services and DTOs
        |
        v
Domain entities, rules, and repository contracts
        ^
        |
Infrastructure adapters (SQLAlchemy, S3, Celery)
```

Controllers validate/shape transport data and delegate. Application services
orchestrate use cases. Domain logic should remain independent of HTTP, ORM,
database, queue, and provider details. Infrastructure implements the required
adapters at the composition boundaries.

## Current layout

```text
backend/app/
  main.py
  core/
    config/
    database/
    exceptions/
    infrastructure/       # shared Celery/task wiring
    logging/
    storage/
  modules/
    audits/
    anomalies/
    processing/
    transactions/
  schemas/models.py        # current shared SQLAlchemy model registry
```

The product and implementation status of each module is documented in the
corresponding root guide: [Audits and Jobs](audits-jobs-module.md),
[Transactions](transactions-module.md), [Processing](processing-module.md),
and [Anomaly Detection](anomalies-module.md).

## Dependency rules

- Controllers depend on application services, DTOs, and boundary dependencies.
- Application services depend on domain abstractions and shared core facilities.
- Domain code owns business rules and repository contracts; it does not depend
  on concrete infrastructure.
- Infrastructure adapters implement domain contracts and translate persistence
  or provider shapes.
- Shared concerns such as settings, database sessions, exceptions, logging, and
  storage belong in `core/`.

The SQLAlchemy models remain in `backend/app/schemas/models.py` as a known
centralization point. New business behavior should not reach into ORM models
directly; module-owned adapters should map them to domain records.

## Validation and errors

Request and response DTOs define explicit API contracts. Domain entities and
services enforce business invariants, and infrastructure validates data read
from external systems. The shared exception handlers provide the common HTTP
error envelope. See [Configuration](config.md), [Database and Migrations](database-and-migration.md),
and [Exception Handling](exceptions.md) for the detailed contracts.

## Testing

The repository uses module-local tests under `backend/app/modules/` and shared
backend tests under `backend/tests/`. Focused tests run from the repository root
with `pytest <path> -q`; the full backend suite runs from `backend/` with
`python -m pytest -q`. Current database-backed integration coverage is tracked
in the module guides and [CI/CD](ci_cd.md).
