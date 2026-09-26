# Audits / Jobs API

This module owns the audit job lifecycle. It currently supports multipart upload to
the configured storage adapter, metadata creation, status retrieval, listing, and
deletion.

## Endpoints

### `POST /v1/audits`

Creates a pending audit job from validated file metadata. The raw file upload, S3 persistence, and asynchronous processing dispatch are deliberately deferred to the storage and processing milestones.

Request example:

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

Returns `201 Created` with the public job metadata. Internal storage coordinates such as the S3 bucket and key are not returned.

### `POST /v1/audits/upload`

Accepts `multipart/form-data` with a required `file` field and optional
`business_label`. The service hashes and stores the file through the storage
abstraction, then creates a pending job. Failed database persistence triggers
storage cleanup.

### `GET /v1/audits`

Lists jobs ordered newest first. Query parameters are `offset` (default `0`) and `limit` (default `50`, maximum `100`).

### `GET /v1/audits/{job_id}/status`

Returns the current job status and metadata. Missing jobs return the standard `RESOURCE_NOT_FOUND` error response.

### `DELETE /v1/audits/{job_id}`

Deletes a job and its database-owned child records through the existing database cascade. Storage deletion will be connected as part of deletion consistency work.

## Boundaries

- Controllers validate transport input and map responses only.
- `JobService` owns use-case orchestration and transaction commits.
- `JobRepository` is a domain-facing protocol.
- `SqlAlchemyJobRepository` is the infrastructure implementation.
- CSV parsing, queue dispatch, processing, results, retry, and export remain outside this first slice.
