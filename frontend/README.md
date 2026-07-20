# Frontend package

This directory will contain the web client for the same repository.

## Intended layout

```text
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

## Notes

- Keep feature modules independent from one another.
- Share UI primitives and API client logic in shared.
- Keep state management and route composition in app.
