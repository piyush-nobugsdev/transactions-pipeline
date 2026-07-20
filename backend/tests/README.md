# Backend tests

Tests should be split by scope so the architecture remains clear.

## Suggested structure

```text
tests/
├── unit/
├── integration/
└── factories/
```

## Testing approach

- Unit tests: validators, domain services, business rules.
- Integration tests: API endpoints, repository behavior, worker flows.
- Factories: reusable test data builders for entities and DTOs.
