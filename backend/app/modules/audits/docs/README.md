# Audits / Jobs API

This module owns the audit job lifecycle. It supports metadata creation, CSV
preview and column mapping, multipart upload to the configured storage adapter,
asynchronous processing dispatch, status retrieval, listing, and deletion.

## Endpoints

### `POST /v1/audits`

Creates a pending job from validated file metadata. The uploaded-file flow is
described below.

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

Accepts `multipart/form-data` with a required `file` field, optional
`business_label`, and optional `column_mappings` JSON object. The API maps the
source headers to the canonical transaction fields before storing and queuing
the CSV. If `column_mappings` is omitted, confident aliases are applied
automatically; if required fields remain missing or ambiguous, the user should
preview the CSV and submit explicit mappings.

`column_mappings` maps canonical field names to the original CSV header text:

```json
{
  "date": "Transaction Date",
  "merchant": "Narration",
  "amount": "Transaction Amount",
  "currency": "Currency Code",
  "status": "Transaction Status",
  "account_id": "Account Number",
  "txn_id": "Reference Number",
  "category": "Transaction Category"
}
```

The six required canonical fields are `date`, `merchant`, `amount`, `currency`,
`status`, and `account_id`. `txn_id` and `category` are optional. Each source
column must exist in the uploaded file and may be selected for only one
canonical field. Unmapped extra columns are omitted. The API stores the
canonicalized CSV, then creates the audit job and dispatches its processing
task. CSV structure and row values are validated by the processing cleaner.
Invalid mappings are rejected before storage.

### `POST /v1/audits/upload/preview`

Accepts multipart `file` and returns the original headers and up to five sample
rows, suggested mappings, per-field `automatic`, `ambiguous`, or `missing`
status and candidate headers, and blocking issues. The selected source headers
can be sent as `column_mappings` to the upload endpoint.

Header matching trims whitespace and ignores case and punctuation. Recognized
aliases include:

| Canonical field | Recognized source header examples |
|---|---|
| `date` | `Date`, `Transaction Date`, `Txn Date`, `Posting Date`, `Value Date` |
| `merchant` | `Merchant`, `Description`, `Narration`, `Particulars`, `Transaction Details`, `Transaction Description`, `Payee`, `Counterparty` |
| `amount` | `Amount`, `Transaction Amount`, `Transaction Value`, `Amount INR`, `Amount USD` |
| `currency` | `Currency`, `Currency Code`, `Transaction Currency`, `Txn Currency` |
| `status` | `Status`, `Transaction Status`, `Txn Status`, `Transaction State` |
| `account_id` | `Account ID`, `Account Number`, `Account No`, `Account`, `Acct Number`, `Acct No` |
| `txn_id` | `Txn ID`, `Transaction ID`, `Transaction Reference`, `Reference Number`, `Reference`, `UTR` |
| `category` | `Category`, `Transaction Category` |

Duplicate headers after normalization are rejected instead of being guessed.
Separate debit and credit (or withdrawal and deposit) columns are not
supported; convert them to a single signed amount column before upload.

### `GET /v1/audits`

Lists jobs ordered newest first. Query parameters are `offset` (default `0`) and `limit` (default `50`, maximum `100`).

### `GET /v1/audits/{job_id}/status`

Returns the current job status and metadata. Missing jobs return the standard `RESOURCE_NOT_FOUND` error response.

### `DELETE /v1/audits/{job_id}`

Deletes a job and its database-owned child records through the existing database cascade. Storage deletion will be connected as part of deletion consistency work.

## Boundaries

- Controllers validate transport input and map responses only.
- Audit application services own mapping and upload/job orchestration.
- `JobService` owns job lifecycle orchestration and transaction commits.
- `JobRepository` is a domain-facing protocol.
- `SqlAlchemyJobRepository` is the infrastructure implementation.
- CSV row parsing/cleaning and transaction persistence are owned by Processing.
  Anomaly detection, results, retry, and export are not yet implemented.
