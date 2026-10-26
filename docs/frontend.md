# Frontend

This document describes the frontend that exists in the repository. The product
target in [Product Requirements](product-requirements.md) specifies React with
Vite; the current implementation instead uses Next.js. That stack difference is
tracked in the [Project Plan](project-plan.md).

## Current implementation

The `frontend/` package uses Next.js 16 and React 19 with TypeScript. Its current
interface is a single audit page:

- selects CSV files and previews headers/sample rows
- preselects confident column matches and allows manual mapping of required and
  optional fields
- submits the upload and optional business label to the API
- polls the audit status endpoint every two seconds until completion or failure
- shows job metadata and processing errors

The client calls the backend directly from the browser. `NEXT_PUBLIC_API_BASE_URL`
sets the API origin and defaults to `http://localhost:8000`.

## Local development

Run the development server from `frontend/`:

```bash
npm run dev
```

Available package scripts are `dev`, `build`, `start`, and `lint`. The standard
local full-stack path is Docker Compose from the repository root; see the root
[README](../README.md).

## Current gaps

- The UI does not yet display transaction results or anomalies, provide exports,
  or expose retry and deletion flows.
- The anomaly scan API is not invoked automatically by the processing worker.
- The current Next.js implementation differs from the Vite target in the
  product requirements.
