# CI/CD Engineering Guide

> **Transaction Pipeline** --- Continuous Integration handbook and
> single source of truth.

## Purpose

This document explains how the CI pipeline works, why each step exists,
lessons learned while building it, and guidelines for safely expanding
it.

------------------------------------------------------------------------

# Pipeline Overview

``` text
Developer Push / PR
        │
        ▼
Checkout Repository
        │
        ▼
Setup Python
        │
        ▼
Install Dependencies
        │
        ▼
Run Ruff
        │
        ▼
Run Unit Tests
        │
        ▼
Create .env
        │
        ▼
Validate Docker Compose
        │
        ▼
Build Docker Images
        │
        ▼
Start Services
        │
        ▼
Wait for API Health
        │
        ▼
Integration Tests
        │
        ▼
docker compose down (always)
```

------------------------------------------------------------------------

# Current Repository Layout

``` text
txn-pipeline/
│
├── .github/workflows/backend-ci.yml
├── docker-compose.yml
├── .env.example
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   └── tests/
└── docs/
```

------------------------------------------------------------------------

# Workflow Philosophy

The workflow verifies the project in increasing levels of confidence.

1.  Static correctness (linting)
2.  Python correctness (unit tests)
3.  Docker correctness
4.  Service startup
5.  Service communication
6.  End-to-end behaviour

Failures should occur as early as possible.

------------------------------------------------------------------------

# Step-by-Step Explanation

## Checkout

Downloads repository contents.

## Setup Python

Installs the required Python version.

## Install Dependencies

Installs everything required to lint and execute tests.

Recommendation:

-   Runtime packages → `requirements.txt`
-   Test/dev packages → `requirements-dev.txt`

## Ruff

Checks formatting and code quality.

## Unit Tests

Fast tests with no external infrastructure.

They should not require Docker.

## Create `.env`

The repository never stores secrets.

CI creates `.env` from `.env.example` and injects secrets if needed.

## Docker Compose Validation

Ensures compose syntax is valid before building.

## Docker Build

Builds production images.

CI should test the image itself.

## Start Services

Starts:

-   PostgreSQL
-   Redis
-   API
-   Celery Worker

## Wait for API

Never assume the API is immediately available.

Wait until `/health` returns HTTP 200.

## Integration Tests

Run against the running API.

Use real HTTP requests (`httpx`) instead of `TestClient`.

This validates:

-   FastAPI
-   Redis
-   Celery
-   Worker
-   Result backend

## Cleanup

Always execute:

``` bash
docker compose down
```

using `if: always()`.

------------------------------------------------------------------------

# Environment Variables

Rules:

-   `.env` is never committed.
-   `.env.example` contains placeholders only.
-   Secrets belong in GitHub Secrets.
-   CI generates `.env`.

------------------------------------------------------------------------

# Unit vs Integration Tests

## Unit

-   Fast
-   No Docker
-   No Redis
-   No Postgres

## Integration

Require running services.

Communicate with the API over HTTP.

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
