# Audits / Jobs Module

This document is the source of truth for the LedgerGuard audits/jobs business module.
It describes the implementation that exists in the backend today, its public API
contract, layer boundaries, persistence behavior, test strategy, and deferred work.

The module is located at:

```text
backend/app/modules/audits/
```

## Purpose

The audits/jobs module owns the lifecycle metadata for an audit job. A job is the
central business record for one future expense-audit workflow.

The current implementation creates and manages pending jobs from metadata or from
multipart file content. Uploaded content is stored through the core storage
abstraction and the job records the resulting object location. The app now
attempts to enqueue the processing task once the job is marked as `processing`.
If that dispatch fails, the job is marked `failed` and the exception is re-raised
instead of leaving a hidden stuck state.

The raw processing pipeline beyond cleaning and persistence remains the next major
milestone. Results, retry, CSV export, and AI classification are still deferred.

## Current Scope

Implemented:

- create a pending audit job
- validate job creation input
- retrieve one job's status and metadata
- list jobs with offset/limit pagination
- delete a job
- map persistence records to domain records
- map domain records to API response DTOs
- return shared application error responses

Not implemented in this module:

- CSV parsing and row-level validation logic beyond the stored file metadata
- S3 download, existence checks, and deletion primitives in the job lifecycle contract
- result retrieval and summary persistence for completed jobs
- anomaly results and LLM classification or narrative summaries
- retrying failed jobs and dead-letter handling
- CSV export and retention cleanup automation
- authentication, authorization, and tenant isolation

The module currently does support upload metadata creation and jobs that are moved to `processing` and then `failed` or `completed` by the pipeline once the Celery worker runs.

## Architecture

The module follows the repository architecture defined in `AGENTS.md`:

```text
HTTP request
    |
    v
controllers/router.py
    |
    v
application DTO validation
    |
    v
application/services/job_service.py
    |
    v
 domain repository protocol
    |
    v
infrastructure/persistence/sqlalchemy_job_repository.py
    |
    v
SQLAlchemy Job model
    |
    v
PostgreSQL
```

### Controllers

Location:

```text
backend/app/modules/audits/controllers/
```

Responsibilities:

- define the HTTP paths and methods
- receive validated request DTOs
- obtain `JobService` through FastAPI dependency injection
- call application use cases
- map domain records to response DTOs
- return HTTP responses

Controllers must not contain business rules, SQLAlchemy queries, storage calls, or
transaction orchestration.

### Application layer

Locations:

```text
backend/app/modules/audits/application/dto/
backend/app/modules/audits/application/mappers/
backend/app/modules/audits/application/services/
```

Responsibilities:

- validate request and response transport shapes
- orchestrate job use cases
- translate missing jobs into `NotFoundError`
- own the application transaction boundary for writes
- map domain records into API response models

`JobService` commits create and delete operations when its repository exposes the
SQLAlchemy session used by the concrete infrastructure adapter. Reads do not commit.

### Domain layer

Locations:

```text
backend/app/modules/audits/domain/entities.py
backend/app/modules/audits/domain/repositories/
```

`JobRecord` is the infrastructure-independent job representation used by the
application layer. `JobRepository` is a protocol that defines the repository
operations required by the application service.

The domain layer must not import FastAPI, SQLAlchemy, PostgreSQL, Celery, S3, or
HTTP response classes.

### Infrastructure layer

Locations:

```text
backend/app/modules/audits/infrastructure/mappers/
backend/app/modules/audits/infrastructure/persistence/
```

`SqlAlchemyJobRepository` adapts the domain repository contract to the existing
SQLAlchemy `Job` model. It owns database queries, inserts, deletes, flushes, and
translation of duplicate-key failures into `ConflictError`.

The infrastructure mapper converts the ORM model into `JobRecord` and prevents the
application layer from depending directly on the ORM model.

## API Contract

The router is registered by `backend/app/main.py` with the prefix `/v1/audits` and
the OpenAPI tag `audits`.

### Create a job

```text
POST /v1/audits
```

Creates a job with initial status `pending`.

Request body:

```json
{
  "filename": "expenses.csv",
  "business_label": "Acme Ltd",
  "file_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "s3_bucket": "ledgerguard-local",
  "s3_key": "audits/example/expenses.csv",
  "file_size_bytes": 2048,
  "content_type": "text/csv",
  "expires_at": "2026-10-22T00:00:00Z"
}
```

Request fields:

| Field | Type | Rules |
|---|---|---|
| `filename` | string | Required, 1-255 characters |
| `business_label` | string or null | Optional, maximum 255 characters |
| `file_hash` | string | Required, exactly 64 hexadecimal characters; normalized to lowercase |
| `s3_bucket` | string | Required, 1-255 characters |
| `s3_key` | string | Required, 1-1024 characters |
| `file_size_bytes` | integer | Required, non-negative |
| `content_type` | string | Required, 1-100 characters |
| `expires_at` | datetime | Required, ISO-8601-compatible datetime |

Unknown request fields are rejected.

Success response: `201 Created`

```json
{
  "id": "8d2f1c65-4a0a-4a10-9f5a-1c5e7342a0d3",
  "filename": "expenses.csv",
  "business_label": "Acme Ltd",
  "status": "pending",
  "file_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "file_size_bytes": 2048,
  "content_type": "text/csv",
  "created_at": "2026-09-22T12:00:00Z",
  "completed_at": null,
  "expires_at": "2026-10-22T00:00:00Z",
  "error_message": null
}
```

The response intentionally does not expose `s3_bucket` or `s3_key`.

### List jobs

```text
GET /v1/audits?offset=0&limit=50
```

Returns jobs ordered by newest `created_at` first.

Query parameters:

| Parameter | Default | Rules |
|---|---:|---|
| `offset` | `0` | Must be greater than or equal to 0 |
| `limit` | `50` | Must be between 1 and 100 |

Success response: `200 OK`

```json
{
  "items": [],
  "offset": 0,
  "limit": 50
}
```

### Get job status

```text
GET /v1/audits/{job_id}/status
```

`job_id` must be a valid UUID. The response uses the same `JobResponse` shape as
job creation.

Success response: `200 OK`

### Upload an audit file

```text
POST /v1/audits/upload
Content-Type: multipart/form-data
```

The request contains a required `file` field and an optional `business_label`.
The service computes the SHA-256 digest, uploads the bytes through `Storage`, and
creates a pending job. Empty files and files larger than `MAX_UPLOAD_SIZE_BYTES`
are rejected. If database persistence fails after the upload, the object is
deleted as compensation.

### Delete a job

```text
DELETE /v1/audits/{job_id}
```

Deletes the job by UUID. The database foreign keys are configured with cascading
deletes for child records such as transactions and summaries.

Success response: `204 No Content`

Storage deletion is not yet coupled to the HTTP delete use case. The storage
adapter supports deletion, but partial database/storage failure behavior must be
defined before production deletion semantics are complete.

## Response and Error Contracts

Successful responses use explicit Pydantic response DTOs:

- `JobResponse`
- `JobListResponse`

Expected errors use the shared exception system in
`backend/app/core/exceptions/`.

| Condition | Status | Error code |
|---|---:|---|
| Invalid request body or query parameter | 422 | `VALIDATION_ERROR` |
| Invalid UUID path parameter | 422 | `VALIDATION_ERROR` |
| Job does not exist | 404 | `RESOURCE_NOT_FOUND` |
| Duplicate business/file hash combination | 409 | `RESOURCE_CONFLICT` |

Error envelope:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found.",
    "details": null
  }
}
```

Controllers do not catch expected exceptions to construct responses manually. They
raise or propagate typed exceptions so the centralized handlers can apply the
shared contract.

## Persistence Model

The module currently uses the existing ORM model:

```text
backend/app/schemas/models.py :: Job
```

The job table includes:

- UUID primary key
- filename
- optional business label
- `JobStatus` enum
- SHA-256 file hash
- S3 bucket and key metadata
- file size and content type
- raw and cleaned row counts
- created and completed timestamps
- expiration timestamp
- optional processing error message

The current status enum is:

```text
pending
processing
completed
failed
```

A uniqueness constraint exists on `(business_label, file_hash)`. A duplicate insert
is translated from `IntegrityError` into `ConflictError` by the repository.

The schema is created by the existing Alembic initial migration:

```text
backend/migrations/versions/8bd2ac0d369b_initial_schema.py
```

## Dependency Injection

The route obtains `JobService` through:

```text
backend/app/modules/audits/controllers/dependencies.py
```

The dependency constructs:

1. the shared `AsyncSession` from `get_db`
2. `SqlAlchemyJobRepository`
3. `JobService`

This keeps FastAPI dependency wiring at the controller boundary and keeps the
service usable with any object implementing the `JobRepository` protocol.

## Testing

The module tests are in:

```text
backend/tests/test_audits_jobs.py
```

They use an in-memory repository and FastAPI dependency overrides. This verifies
real request validation, route behavior, service orchestration, response mapping,
not-found behavior, deletion behavior, and public-field filtering without requiring
PostgreSQL or Redis.

Run the backend suite from the backend directory:

```powershell
Set-Location D:\projects\txn-pipeline\txn-pipeline\backend
python -m pytest -q
```

Run collection-only validation when adding or moving module packages:

```powershell
python -m pytest --collect-only -q
```

The module follows the repository rule that every test includes a comment describing
what behavior it verifies.

## Logging and Correlation

The application middleware establishes the API logging context. The current audit
routes do not generate a separate job-processing task, so processing-stage
correlation will be added when queue dispatch is implemented.

When asynchronous processing is introduced, the job UUID must be passed explicitly
to the worker and included in the worker logging context according to
`docs/structured-logging-and-correlation.md`.

## Planned Extensions

The next additions should preserve the current boundaries:

1. Connect storage deletion to the job deletion use case.
2. Add a queue dispatcher abstraction and dispatch a processing job after upload.
3. Add explicit job state transition rules for `pending`, `processing`, `completed`, and `failed`.
4. Add transaction/result queries without exposing ORM models to controllers.
5. Add retry and export use cases.
6. Add integration tests against PostgreSQL and the storage/queue adapters.
7. Add authentication and tenant/business ownership checks before exposing jobs beyond local development.

These extensions must not put S3, Celery, CSV parsing, or processing algorithms into
`controllers/` or the domain entity.

## Source Files

- [Module package](../backend/app/modules/audits/)
- [Router](../backend/app/modules/audits/controllers/router.py)
- [Request DTO](../backend/app/modules/audits/application/dto/request/job_requests.py)
- [Response DTOs](../backend/app/modules/audits/application/dto/response/job_responses.py)
- [Application service](../backend/app/modules/audits/application/services/job_service.py)
- [Domain entity](../backend/app/modules/audits/domain/entities.py)
- [Repository contract](../backend/app/modules/audits/domain/repositories/job_repository.py)
- [SQLAlchemy repository](../backend/app/modules/audits/infrastructure/persistence/sqlalchemy_job_repository.py)
- [Tests](../backend/tests/test_audits_jobs.py)
- [Plan](../plan.md)
- [Architecture rules](../AGENTS.md)
