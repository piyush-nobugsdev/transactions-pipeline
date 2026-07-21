# Backend package

This directory will hold the backend service for the monorepo.

## Intended layout

```text
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── domain/
│   ├── infrastructure/
│   ├── modules/
│   └── shared/
├── tests/
├── alembic/
└── requirements.txt
```

## Notes

- Keep API routes thin and focused on transport concerns.
- Put business rules in domain services.
- Keep persistence and external integrations behind the infrastructure layer.
- Keep cross-cutting concerns centralized in core.
- Raise typed application exceptions from services and domain code; FastAPI converts them globally into consistent JSON error responses.
- Avoid route-level try/except blocks for expected domain errors; use the shared exception handlers instead.
