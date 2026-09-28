# Processing Module

This document is the root-level source of truth for the Processing business module. It describes the current implementation in `backend/app/modules/processing/`, its pipeline contract, boundaries, tests, and remaining work. Update it whenever processing behavior or its dependencies change.

## Purpose and scope

Processing orchestrates one audit job's asynchronous pipeline. Its first implemented stage downloads the job's source CSV through the storage abstraction, validates and normalizes supported rows, removes exact duplicates, persists normalized transaction records through the Transactions repository contract, and updates the job's counts and state.

Processing is an orchestrator, not an owner of S3, Celery, SQLAlchemy, anomaly algorithms, or AI provider behavior. The Celery task and persistence wiring live under the module's infrastructure boundary. CSV parsing/cleaning is a pure domain service.

## Current implementation status

Implemented:

- pure CSV validation and normalization service
- supported mixed date formats: `YYYY-MM-DD`, `DD-MM-YYYY`, and `YYYY/MM/DD`
- amount parsing that strips `$`, `₹`, and thousands separators; values must be positive
- uppercasing of currency and transaction status
- blank category defaulting to `Uncategorised`
- exact duplicate removal using `(txn_id, date, amount, merchant)`
- processing application service which loads job metadata, downloads stored content, persists normalized rows through transaction repository bulk-create, records raw/clean row counts, and marks the job completed
- failure handling which rolls back the processing transaction, marks the job failed with a bounded error message, commits that failure state, then re-raises for Celery visibility
- module-owned Celery task adapter, registered in the Celery app include list
- module tests for successful CSV processing and invalid-header failure behavior
- domain ownership of `JobStatus`, `TransactionStatus`, and `AnomalyReason`; SQLAlchemy models import these domain enums
- pytest discovery includes `backend/app/modules` so module-local tests run in the regular backend test suite

Not implemented:

- anomaly detection
- LLM transaction classification or narrative summary
- `JobSummary` persistence and result retrieval
- export generation
- retry/resume semantics or idempotent transaction replacement on repeated task delivery
- upload row-count cap and broader CSV size/encoding policy beyond UTF-8 validation
- database-backed integration tests for the complete worker pipeline

This is the first real data-processing slice, not the complete PRD pipeline.

## Architecture and source layout

```text
Celery task adapter
    -> ProcessingService
        -> JobRepository protocol
        -> Storage protocol
        -> TransactionRepository protocol
        -> UnitOfWork protocol
        -> pure CSV cleaner

Infrastructure adapter constructs SQLAlchemy repositories, S3 storage, and an async session.
```

| Layer | Location | Responsibility |
|---|---|---|
| Domain service | `backend/app/modules/processing/domain/services/csv_cleaner.py` | Validate CSV structure and normalize/deduplicate rows without I/O |
| Application | `backend/app/modules/processing/application/services/processing_service.py` | Orchestrate download, cleaning, transaction persistence, state changes, commit/rollback |
| Infrastructure worker | `backend/app/modules/processing/infrastructure/worker.py` | Celery entry point and construction of database/storage adapters |
| Tests | `backend/app/modules/processing/tests/test_processing_service.py` | Behavior tests using real cleaner logic and in-memory boundary adapters |

The Processing application layer depends on repository/storage/unit-of-work protocols. It does not import SQLAlchemy models or the Celery API. The worker is the composition boundary where concrete infrastructure is assembled.

## CSV contract

The CSV header is required and is normalized by trimming whitespace and lowercasing names. The required columns are:

- `date`
- `merchant`
- `amount`
- `currency`
- `status`
- `account_id`

The optional columns are `txn_id` and `category`. Unknown columns, duplicate normalized headers, missing required headers, malformed UTF-8, rows with extra values, empty merchants/accounts, invalid dates/currencies/statuses, and non-positive amounts fail processing. Entirely blank rows are ignored.

For each nonblank data row, `row_count_raw` increases before cleaning. `row_count_clean` is the number of normalized records after exact duplicate removal. The cleaner currently accepts only UTF-8/UTF-8 BOM input. Currency is uppercased and must be three alphabetic characters. Status must match the domain `TransactionStatus` values (`SUCCESS`, `FAILED`, `PENDING`).

Exact duplicate key:

```text
(txn_id, date, amount, merchant)
```

This is row deduplication only; near-duplicate payment detection belongs to the future Anomaly Detection module.

## Processing lifecycle

1. Load the job by UUID; missing jobs fail with the shared not-found error.
2. Set status to `processing`, clear prior completion/error metadata, and commit this transition.
3. Download the object using the job's `s3_key` from the configured Storage adapter.
4. Validate and clean CSV rows.
5. Persist all normalized rows through `TransactionRepository.bulk_create` in the current unit of work.
6. Set status to `completed`, store raw/clean row counts and completion timestamp, and commit transaction rows and job completion together.
7. On processing error, roll back uncommitted transaction data, mark the job `failed` with a safe bounded message, commit that state, and re-raise the original exception so Celery records task failure.

The processing session commits the initial `processing` state separately. Transaction persistence and final completion state share the subsequent session transaction. A redelivered task is not yet idempotent: existing transactions are not cleared/replaced, so retries may duplicate data. Do not enable automatic retries until this behavior is resolved.

## Celery integration

The worker task name remains `app.core.infrastructure.tasks.process_audit_job` for compatibility with the dispatch call in the Audits module. Its implementation is owned by `backend/app/modules/processing/infrastructure/worker.py` and is registered through the Celery app's include list. API/application orchestration dispatches by task name and does not import the worker implementation.

## Validation and errors

- CSV validation errors are explicit `ValueError` subclasses and are stored as the job error message.
- Unexpected infrastructure or programming failures are logged with job correlation and stored as a generic safe message; the exception is re-raised.
- Error messages written to `Job.error_message` are capped at 2,000 characters.
- Transaction row validation is applied by the CSV cleaner before persistence; repository/database constraints remain a second boundary.

## Testing and verification

The module tests exercise actual CSV parsing, normalization, deduplication, persistence delegation, completion counts, and invalid-header failure behavior. The transaction module's existing API tests are also now included by pytest discovery.

Run from `backend/`:

```powershell
python -m pytest app/modules/processing/tests app/modules/transactions/tests -q
```

A full backend suite should be run before merging. A database-backed worker integration test is still required; current processing tests use in-memory adapters for repository and unit-of-work boundaries.

## Next work

1. Add upload row-count limits and settle CSV schema/size policies from the PRD.
2. Add idempotent processing semantics before configuring Celery retries.
3. Add database integration coverage for rollback, transaction persistence, and job state changes.
4. Build the Anomaly Detection module and insert it after cleaning/persistence according to the planned orchestration boundary.
5. Add AI classification and narrative summary stages as separate module/provider contracts.
6. Persist `JobSummary`, add result retrieval, and then implement CSV export.
7. Add cleanup/retention integration and revisit security/authorization before public deployment.
