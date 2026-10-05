# Transactions Module

This document is the root-level source of truth for the Transactions business module. It describes the implementation currently present in `backend/app/modules/transactions/`, the persistence model it uses, the HTTP contract, architectural boundaries, verification status, and work that remains. Update this document when the module contract or implementation changes.

## Purpose and ownership

The Transactions module owns normalized transaction records associated with audit jobs. Its current responsibilities are creating one transaction, retrieving one transaction, listing transactions (optionally filtered by job), and deleting one transaction.

The module does not currently parse CSV files, normalize input rows as a pipeline stage, detect anomalies, classify transactions, generate summaries, or export CSV. Those behaviors belong in later processing, anomaly, AI, or audit-result work and should call the transaction domain/repository contract rather than reaching into SQLAlchemy models.

## Current implementation status

Implemented in the current source tree:

- module-local controller, application service, request/response DTOs, response mapper, domain record, repository protocol, and SQLAlchemy repository
- `POST`, `GET` collection, `GET` by ID, and `DELETE` endpoints
- optional job filtering and offset/limit pagination on the collection endpoint
- request field validation through Pydantic
- ORM-to-domain mapping in the persistence adapter
- router registration in the backend app factory
- initial module-local API tests using an in-memory repository

Not yet complete or verified:

- the module still needs database-backed integration coverage beyond the in-memory API tests
- bulk creation exists only as a repository protocol/adapter method and is still not exposed through a public application use case or HTTP endpoint
- no transaction update endpoint or export support exists
- the create endpoint still accepts anomaly and LLM-related fields from callers; public write permissions should be narrowed before production exposure
- transaction creation does not yet verify the associated job through an application-level use case; the database foreign key is still the current integrity boundary
- authentication, authorization, and tenant ownership checks are not implemented

The most important reliability fix is now in place: `TransactionService` explicitly commits after create/delete when the repository exposes a session. This prevents a request-scoped session from silently closing with an uncommitted write. The module is still an initial API and persistence slice, but the durable write bug is corrected.

## Architecture and source layout

The intended dependency direction follows `AGENTS.md`:

```text
HTTP controller
    -> application DTO / service / mapper
        -> domain entity and repository protocol
            <- SQLAlchemy repository adapter
                -> shared SQLAlchemy Transaction model
```

Current files:

| Layer | Files | Responsibility |
|---|---|---|
| Controller | `backend/app/modules/transactions/controllers/router.py`, `dependencies.py` | HTTP routes, FastAPI dependency construction, response mapping |
| Application | `backend/app/modules/transactions/application/services/transaction_service.py` | Use-case orchestration and UUID conversion |
| Application DTOs | `backend/app/modules/transactions/application/dto/request/transaction_requests.py`, `response/transaction_responses.py` | Request validation and explicit response shape |
| Application mapper | `backend/app/modules/transactions/application/mappers/transaction_mapper.py` | Domain record to response DTO |
| Domain | `backend/app/modules/transactions/domain/entities.py`, `repositories/transaction_repository.py` | Transaction record and repository contract; enum imports currently couple the entity to the shared model package |
| Infrastructure | `backend/app/modules/transactions/infrastructure/persistence/sqlalchemy_transaction_repository.py` | SQLAlchemy operations and persistence-to-domain mapping |
| Tests | `backend/app/modules/transactions/tests/test_transaction_service.py` | In-memory API behavior tests; currently outside configured pytest discovery |
| Local notes | `backend/app/modules/transactions/docs/README.md` | Brief module-local orientation; this root document is authoritative |

The ORM model currently remains in `backend/app/schemas/models.py` as `Transaction`. New domain behavior must not import or depend on that ORM module. Follow the package-depth import guidance in `AGENTS.md`; prefer absolute imports if relative depth is unclear.

## Data model

The persistence table is `transactions`. Its current columns are:

| Field | Type / constraints | Meaning |
|---|---|---|
| `id` | UUID primary key | Generated transaction record ID |
| `job_id` | UUID, non-null, indexed, FK to `jobs.id`, `ON DELETE CASCADE` | Owning audit job |
| `txn_id` | Optional string, max 255 | Source transaction identifier |
| `date` | Non-null date, indexed | Transaction date |
| `merchant` | Non-null string, max 500 | Merchant name |
| `amount` | Non-null numeric(18, 2) | Transaction amount |
| `currency` | Non-null string, max 3 | Currency code |
| `status` | Non-null `TransactionStatus` enum | Current values: `SUCCESS`, `FAILED`, `PENDING` |
| `category` | Non-null string, max 255; ORM default `Uncategorised` | Base transaction category |
| `account_id` | Non-null string, max 255 | Source account identifier |
| `is_anomaly` | Non-null boolean; ORM default `false` | Whether the row is flagged as anomalous |
| `anomaly_reason` | Optional `AnomalyReason` enum | Current values: `statistical_outlier`, `currency_mismatch`, `duplicate_payment` |
| `duplicate_of_txn_id` | Optional string, max 255 | Related source transaction identifier for a duplicate |
| `llm_category` | Optional string, max 255 | AI-provided category |
| `llm_raw_response` | Optional text | Stored raw AI response |
| `llm_failed` | Non-null boolean; ORM default `false` | Whether AI processing failed for the row |

The standalone ORM table has no uniqueness rule for `txn_id`, and no relationship object is currently declared. Job deletion cascades through the database foreign key. Database enum values and constraints are defined by the model and migration; change both via an Alembic migration when they evolve.

The domain record mirrors these fields but is a dataclass. It currently uses `TransactionStatus` and `AnomalyReason` from the shared schema/model module; that coupling is a known architecture gap.

## HTTP API

The router is registered at `/v1/transactions` by `backend/app/main.py`. Responses use explicit DTOs. The collection response is `{ "items": [...], "offset": number, "limit": number }`.

### Create transaction

`POST /v1/transactions` returns `201 Created` with a `TransactionResponse`.

Request fields:

- required: `job_id` (UUID string), `date` (ISO date), `merchant` (1-500 chars), `amount` (decimal greater than zero), `currency` (exactly 3 characters), `account_id` (1-255 chars)
- optional: `txn_id`, `status`, `category`, `is_anomaly`, `anomaly_reason`, `duplicate_of_txn_id`, `llm_category`, `llm_raw_response`, `llm_failed`
- defaults: `status=PENDING`, `category=Uncategorised`, `is_anomaly=false`, `llm_failed=false`; other optional values default to `null`
- unknown fields are rejected (`extra="forbid"`)
- currency is uppercased; merchant is stripped of leading/trailing whitespace

Example:

```json
{
  "job_id": "d1a07dce-bbb5-41dc-a99c-a1865fd18f97",
  "txn_id": "txn-001",
  "date": "2026-03-01",
  "merchant": "Example Merchant",
  "amount": "42.50",
  "currency": "USD",
  "status": "PENDING",
  "category": "Office Supplies",
  "account_id": "acct-001"
}
```

The service parses `job_id` to a UUID and calls the repository. `TransactionService` now commits after create/delete when the repository exposes a session, so the endpoint is safe for durable writes under the current repository/session boundary.

### List transactions

`GET /v1/transactions?job_id=<uuid>&offset=0&limit=50` returns `200 OK`.

- `job_id` is optional; when present, only records for that job are selected
- `offset` defaults to `0` and must be non-negative
- `limit` defaults to `50` and must be between `1` and `100`
- current persistence ordering is newest transaction date first

### Get transaction

`GET /v1/transactions/{transaction_id}` returns `200 OK`. Invalid UUID path values are rejected by FastAPI validation. A missing record produces the shared `RESOURCE_NOT_FOUND` error response.

### Delete transaction

`DELETE /v1/transactions/{transaction_id}` returns `204 No Content`. A missing record produces the shared `RESOURCE_NOT_FOUND` response. The application service commits the repository session after a successful delete so the row is durable before the request returns.

## Repository contract

`TransactionRepository` is a domain-facing protocol with:

- `create(**data) -> TransactionRecord`
- `bulk_create(records) -> list[TransactionRecord]`
- `get(transaction_id) -> TransactionRecord | None`
- `list(job_id=None, offset=0, limit=50) -> list[TransactionRecord]`
- `delete(transaction_id) -> bool`

The SQLAlchemy implementation is in `infrastructure/persistence/`. It maps ORM objects to `TransactionRecord` and performs the query filtering, ordering, pagination, and delete. Its current `bulk_create` loops over `create`; it is not an atomic or optimized bulk operation. The application service currently does not expose bulk creation.

## Error and validation behavior

- DTO validation failures use the shared FastAPI validation handler and return the project's structured validation error response.
- Missing IDs are converted to `NotFoundError("transaction")` by the application service.
- Persistence `create` currently catches broad exceptions, rolls back the session, and converts them to `ConflictError`; the exception mapping should be narrowed before treating persistence failures as clear API conflicts.
- Database foreign-key violations remain a persistence-level integrity boundary for nonexistent jobs.

## Testing and verification

The module-local tests exercise create response, list-by-job behavior, and delete/lookup behavior through an in-memory repository. They do not yet exercise the real SQLAlchemy adapter or database.

`backend/pytest.ini` now includes both `tests` and `app/modules`, so the transaction module tests are collected in the normal backend suite. The remaining work is to add database-backed repository/integration coverage and a proper application-level bulk-create contract.

## Completion work and recommended order

1. Establish transaction commit/rollback ownership and test durable create/delete behavior against the configured database.
2. Move enums into the transaction domain (or a deliberate shared domain package) and remove domain imports from ORM modules.
3. Ensure module tests are discovered by the configured test command; add unit and repository integration coverage.
4. Narrow create-field permissions so clients cannot set processing-owned anomaly/LLM fields; validate job existence/ownership at the right application boundary.
5. Expose an application-level bulk-create use case for the processing pipeline and make it transactional and appropriately efficient.
6. Add query requirements driven by result views, then implement export preparation/contract when the audit export use case is defined.
7. Decide whether public transaction mutation/deletion endpoints are appropriate; restrict them or keep transaction writes internal to the pipeline if not.

## Architecture rules for future changes

- Keep controllers limited to transport validation, delegation, and response DTOs.
- Keep request and response contracts in module-local DTO packages.
- Keep business invariants and enums in domain-owned types; do not import SQLAlchemy models into domain/application logic.
- Keep repository protocols in the domain layer and concrete database logic in infrastructure.
- Have processing depend on the transaction repository abstraction or application use case, not on SQLAlchemy classes.
- Keep cross-cutting concerns in `backend/app/core/` and validate external input at the boundary.
- Update this document and `plan.md` alongside behavior or contract changes.
