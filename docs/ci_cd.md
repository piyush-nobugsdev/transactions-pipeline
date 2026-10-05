# CI/CD Engineering Guide

This document reflects the current repository reality. The project still includes
working Python tests, a working Docker compose definition, and environment
validation that runs before runtime. The primary implementation focus remains the
backend feature pipeline, not a fully matured upstream CI platform.

## Current repository status

The project currently supports:

- Python backend validation through `python -m app.core.config`
- local Docker orchestration with PostgreSQL, Redis, API, and worker services
- backend pytest runs from the `backend` folder
- linting via Ruff in the normal development workflow

The repo is not yet at the point where a complete end-to-end production pipeline
is enforced in CI, but the foundations for validation and service startup are in
place.

## Recommended CI flow

1. Checkout repository
2. Set up Python
3. Install dependencies
4. Run environment validation
5. Run linting and unit tests
6. Create a local `.env` from the repository template if required by the job
7. Validate `docker-compose.yml`
8. Build Docker images
9. Start services
10. Wait for health checks
11. Run focused integration checks when the service stack is running
12. Always tear down the stack in cleanup

## Environment validation

The backend config layer is the single source of truth for runtime env values.
The command below should be treated as a required gate before the app is started:

```bash
cd backend
python -m app.core.config
```

This validates required fields and exits non-zero if configuration is missing or
invalid. It also redacts secrets before printing any config snapshot.

## Testing expectations

The repo currently has a good set of backend tests under:

- `backend/tests/`
- `backend/app/modules/processing/tests/`
- `backend/app/modules/transactions/tests/`
- module-specific audit tests in the same backend tree

The recommended default local command is:

```bash
cd backend
python -m pytest -q
```

For a focused validation pass before a merge, use the module-level tests most
relevant to the changed behavior and then run the full backend suite as the final
check.

## Docker and stack validation

The compose file is the source of truth for the local development stack. It should
be validated before starting the backend in a CI environment:

```bash
docker compose config --quiet
```

This catches invalid compose syntax and broken env references before the build
step.

## Operational guidance

- Keep secrets out of repo files and commit templates.
- Validate config early so missing env values fail the pipeline fast.
- Use a dedicated job for backend tests rather than relying on a partial smoke run.
- Keep Docker verification and backend pytest separate so failures are easier to isolate.
- Re-run the full backend suite after any change to job state, transaction writes,
  config security, or queue dispatch behavior.

## Current gaps

The project still needs additional hardening for production-grade CI, especially:

- broader end-to-end coverage against the live stack
- explicit test coverage for background worker retries and idempotency
- integration tests for S3 and database-backed flows
- full policy alignment between docs and runtime behavior as the pipeline evolves

These gaps are known and should be treated as follow-up work, not as a reason to
ignore the existing validation gates that are already in place.


## Tests and current CI configuration

- Current repo configuration: the main CI workflow validates the environment,
  runs linting, verifies Docker compose, and builds the stack, but does not
  currently execute the backend pytest suite in the primary job. The repo still
  contains a working unit-test suite, and the first recommended follow-up is to
  re-enable it in a dedicated CI job for PR feedback while keeping Docker build
  validation in place.

- About `backend/tests/test_config.py`:
        - Type: Unit test (no Docker required). It verifies that the `Settings`
                model reads environment variables correctly using `pytest`'s `monkeypatch`.
        - Running in CI: the CI job creates `.env` from `.env.example` early in the
                pipeline. If the test is re-enabled, CI will have those env values and the
                test should pass in CI.
        - Local developer note: running pytest locally without an `.env` file may
                cause the test to fail because `Settings` declares required fields
                (for example `POSTGRES_USER`). To make unit tests robust and runnable on
                developer machines, prefer one of the following:
                - Monkeypatch all required env vars inside the test.
                - Instantiate `Settings` with explicit overrides in tests.
                - Provide defaults for truly optional fields in `Settings` (use
                        cautiously — required production config should usually stay required).

- Recommendation: keep fast unit tests on the runner for PR feedback and run
        integration tests in a separate `integration` job that uses `docker compose`
        to bring up services. This balances fast feedback with environment fidelity.

------------------------------------------------------------------------

# Lessons Learned

## Missing httpx

### Symptom

    ModuleNotFoundError: httpx

### Cause

`TestClient` depends on `httpx`.

### Fix

Install `httpx`.

------------------------------------------------------------------------

## Wrong Working Directory

### Symptom

Docker couldn't find `.env`.

### Cause

A global

``` yaml
working-directory: api
```

created `api/.env`.

Docker expected the file beside `docker-compose.yml`.

### Rule

Use `working-directory` only for Python steps.

Run Docker commands from the repository root.

------------------------------------------------------------------------

## Missing .env

### Symptom

    env file .env not found

### Fix

Create `.env` before Docker starts.

------------------------------------------------------------------------

## Bind Mounts in CI

Originally:

``` yaml
volumes:
  - ./api/app:/code/app
```

This caused import problems inside CI.

### Rule

Use bind mounts for local development only.

CI should test the built image.

------------------------------------------------------------------------

## API Startup Failures

Never assume containers are healthy because they started.

Always inspect:

``` bash
docker compose ps
docker compose logs api
docker compose logs worker
```

------------------------------------------------------------------------

## TestClient vs httpx

`TestClient` executes the application inside pytest.

Integration tests should instead use

``` python
httpx.get("http://localhost:8000")
```

to exercise the running container.

------------------------------------------------------------------------

# CI Debugging Playbook

## API unreachable

1.  docker compose ps
2.  docker compose logs api
3.  Check `/health`

## Worker not processing tasks

1.  docker compose logs worker
2.  Verify registered tasks.
3.  Check Redis connectivity.

## Task remains PENDING

Verify:

-   worker received task
-   broker URL
-   result backend
-   worker logs

------------------------------------------------------------------------

# Guidelines for Future Tests

Before adding a test ask:

-   Does it require Docker?
-   Does it require Postgres?
-   Does it require Redis?
-   Can it remain a unit test?

Prefer unit tests whenever possible.

------------------------------------------------------------------------

# Expanding the Pipeline

Future additions:

-   Migration tests
-   Coverage reporting
-   Security scanning
-   Dependency vulnerability scanning
-   Image scanning
-   Deployment
-   Smoke tests after deployment

------------------------------------------------------------------------

# Engineering Principles

-   Fail early.
-   Keep unit tests independent.
-   Integration tests use real services.
-   CI should mirror production.
-   Never commit secrets.
-   Prefer reproducible builds.
-   Document every major debugging session.

------------------------------------------------------------------------

# Final Checklist

Before merging:

-   Ruff passes
-   Unit tests pass
-   Docker builds
-   API starts
-   Worker starts
-   Integration tests pass
-   Cleanup succeeds

When a new issue is discovered, update this document so the same
debugging effort is never repeated.
