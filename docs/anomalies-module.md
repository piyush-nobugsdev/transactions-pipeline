# Anomaly Detection Module

This page is the source of truth for the current anomaly-detection implementation.
The product target is described in [Product requirements](product-requirements.md);
the current worker integration is described in [Processing](processing-module.md).

## Scope and status

The module has a pure domain detector, an application service, SQLAlchemy-backed
transaction access, request/response DTOs, and API routes under
`backend/app/modules/anomalies/`. It evaluates duplicate payments, statistical
outliers, and currency mismatches, and persists the first selected reason to
transaction anomaly fields.

The module is currently invoked through its API only. The Celery processing
pipeline does **not** call it yet, so uploaded jobs do not receive automatic
anomaly analysis. Job result retrieval, anomaly grouping in the audit results
API, and integration coverage against a real database are also outstanding.

## API

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/v1/anomalies/scan` | Runs detection for the supplied job and writes findings to transaction records. |
| `GET` | `/v1/anomalies?job_id=<uuid>` | Currently runs the same detection-and-write operation; it is not a read-only listing route. |

`POST /v1/anomalies/scan` accepts JSON with a required `job_id` UUID and an
optional `outlier_multiplier` decimal (default `3.0`, minimum `1.0`). The
response includes the job ID, number of transactions loaded, number of findings,
and the findings. Each finding contains transaction and job IDs, merchant,
amount, currency, account, reason, and an optional related transaction ID.

The repository currently loads at most 50 transactions per call. No pagination
or job-existence check is implemented separately; a job with no transaction
records currently produces the shared not-found error. Treat both endpoints as
development functionality until these API semantics are made explicit and
covered by integration tests.

## Detection rules as currently implemented

Rules are evaluated in this order:

1. **Duplicate payment.** Compare transactions for equal account IDs and merchant
   names after lowercasing and removing non-alphanumeric characters. Amounts
   match when their relative difference is at most 1% of the larger absolute
   amount; dates must be no more than three days apart. Each matching pair
   produces findings for both transactions. The related identifier uses the
   other transaction's `txn_id`, falling back to its record UUID.
2. **Statistical outlier.** For each transaction, calculate the median amount of
   the other loaded transactions with the same account ID. Flag when its amount
   is greater than the median multiplied by the requested multiplier (or `3.0`
   for the GET route). The comparison does not currently separate currencies or
   transaction statuses.
3. **Currency mismatch.** Flag a transaction in `USD` when its normalized
   merchant matches a built-in domestic-merchant name. The current built-in set
   is defined in `domain/services/anomaly_detector.py`; it is not loaded from
   business-specific configuration or `AuditRule`.

Transactions selected by the duplicate rule are not evaluated by later rules in
the same scan. Other transactions keep only the first matching reason. Exact
duplicate source rows are not explicitly excluded by checking `txn_id`; exact
row removal is currently done earlier by the CSV cleaner.

## Persistence and known limitations

The service writes `is_anomaly`, `anomaly_reason`, and
`duplicate_of_txn_id` to the transaction repository and commits through the
SQLAlchemy session. Repeated scans are not read-only: they recompute findings and
write them again. A scan does not clear a previously stored anomaly flag when a
transaction no longer matches a rule.

Additional limitations to resolve before treating this as production-ready:

- The 50-record repository limit means larger jobs are only partially analyzed.
- Duplicate matching does not compare currencies or explicitly reject identical
  source transaction IDs.
- Pairwise matching can produce multiple findings for a transaction when it
  matches several other records; the response count is the number of findings,
  not necessarily unique anomalous transactions.
- Outlier baselines mix currencies and use the other loaded records, rather than
  a complete account-level dataset with normalized currency handling.
- The default domestic merchant set and currency assumptions are hard-coded;
  the PRD's business-specific rules are not wired in.
- The API scan/list behavior and persistence do not yet have database-backed
  integration tests.
- The application service currently imports a repository protocol declared in
  the infrastructure package, despite a domain repository contract also
  existing; align the service and adapter with the domain contract to preserve
  the required inward dependency direction.
- Processing does not invoke anomaly detection, and there is no audit results
  endpoint that returns persisted findings.

## Tests

The current unit tests cover a positive example for each detector. They do not
yet cover threshold boundaries, rule priority, repeat scans, large jobs,
duplicate-pair multiplicity, or database persistence.

Run the focused tests from the repository root:

```powershell
pytest backend/app/modules/anomalies/tests -q
```

## Source layout

- Detector: `backend/app/modules/anomalies/domain/services/anomaly_detector.py`
- Application orchestration: `backend/app/modules/anomalies/application/services/anomaly_service.py`
- API routes: `backend/app/modules/anomalies/controllers/router.py`
- Persistence adapter: `backend/app/modules/anomalies/infrastructure/persistence/`
- Tests: `backend/app/modules/anomalies/tests/`
