# Transaction Pipeline

AI-assisted transaction auditing: CSV intake, asynchronous processing,
transaction normalization, anomaly scanning, and planned AI classification and
reporting.

## Current status

CSV upload and preview, job lifecycle APIs, asynchronous cleaning and normalized
transaction persistence, and API-driven anomaly scanning are implemented. The
anomaly scanner is not yet part of the worker pipeline. AI classification,
narrative summaries, job result retrieval, export, and production operational
hardening remain outstanding.

## Run locally

Start the application stack from the repository root:

```bash
docker compose up --build
```

The default stack serves the frontend at `http://localhost:3000`, API health at
`http://localhost:8000/health`, and FastAPI OpenAPI UI at
`http://localhost:8000/docs`. Use `docker compose down` to stop it. See
[Project Documentation](docs/README.md) for setup and operational details,
requirements, architecture, module contracts, and the current roadmap.

The project uses Docker Compose for the API, worker, frontend, PostgreSQL, and
Redis. Environment defaults and override behavior are documented in
[Configuration](docs/config.md).
