# LedgerGuard — AI-Powered Expense Audit Tool for Small Businesses

## 0. Problem & Positioning

Small business owners and shop proprietors in India hand their CA a pile of bank
statements / expense CSVs every month. Before the CA can do anything useful with
it, someone has to manually catch the boring-but-costly stuff:

- duplicate vendor payments (paid twice for the same invoice, common when paying
  via UPI + bank transfer back-to-back)
- currency/account mismatches (a "domestic-only" vendor charged in USD — usually
  a data entry error or a card fraud signal)
- statistical outliers (one transaction wildly bigger than the account's normal
  pattern — could be a typo, could be fraud, could be a one-off legit purchase
  that's worth flagging anyway)
- unlabeled/uncategorized spend that makes the monthly P&L unreadable

**LedgerGuard** is a backend service that takes a raw, messy transaction export,
cleans it, flags the above issues automatically, classifies spend into categories
using an LLM, and hands back a plain-language summary — so the business owner (or
their CA) spends their time on judgment calls, not data entry.

This is explicitly a **pre-bookkeeping audit layer**, not a full accounting system.
It doesn't replace Tally/Zoho Books — it's the thing you run *before* those, to
clean up and flag what's worth a human's attention.

**Time constraint:** 2-day build for v1. Prioritize a fully working end-to-end
flow over polish. Cut scope (Section 8) before cutting correctness of the core
pipeline.

---

## 1. Core User Story

> "I'm a small business owner / I'm a CA with 15 small-business clients. Every
> month I get a CSV export of bank + UPI transactions. I upload it, and a few
> minutes later I get back: a cleaned ledger, a list of 'these N transactions
> look off, check them,' a spend breakdown by category, and a 3-sentence summary
> I can literally forward to my client or paste into a WhatsApp message."

---

## 2. Tech Stack (Decided)

| Layer | Choice | Why |
|---|---|---|
| API Framework | **FastAPI** | Lower boilerplate than DRF; async-native; familiar routing/DI patterns coming from NestJS/Express |
| Database | **PostgreSQL** | Relational integrity for jobs/transactions; required by spec |
| ORM | **SQLAlchemy 2.0 (async)** + **Alembic** for migrations | Standard pairing with FastAPI |
| Job Queue | **Celery + Redis** | Async processing required; Celery is the most documented option, easiest to debug under time pressure |
| LLM | **Gemini 1.5 Flash (free tier)** | No billing setup required, fast, generous free quota |
| Containerization | **Docker + Docker Compose** | Single-command startup required |
| Data cleaning | **pandas** | Fast for CSV normalization |
| Retry logic | **tenacity** | Decorator-based retries with exponential backoff, minimal code |

---

## 3. Data Model

### Job (one per uploaded statement/export)
| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| filename | str | |
| business_label | str, nullable | optional client/shop name for multi-client use (e.g. a CA running this for several clients) |
| status | enum | `pending`, `processing`, `completed`, `failed` |
| file_hash | str | SHA-256 of raw upload, used for idempotent re-upload detection |
| row_count_raw | int | |
| row_count_clean | int | |
| created_at | datetime | |
| completed_at | datetime, nullable | |
| error_message | str, nullable | |

### Transaction
| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| job_id | FK → Job | |
| txn_id | str, nullable | original may be blank |
| date | date | normalized ISO 8601 |
| merchant | str | |
| amount | numeric | symbols stripped |
| currency | str | uppercased: INR / USD |
| status | str | uppercased: SUCCESS / FAILED / PENDING |
| category | str | 'Uncategorised' if missing pre-LLM |
| account_id | str | |
| is_anomaly | bool | |
| anomaly_reason | str, nullable | `statistical_outlier`, `currency_mismatch`, `duplicate_payment` |
| duplicate_of_txn_id | str, nullable | set when `anomaly_reason = duplicate_payment` |
| llm_category | str, nullable | filled post-LLM classification |
| llm_raw_response | text, nullable | raw LLM response for debug |
| llm_failed | bool, default False | |

### JobSummary
| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| job_id | FK → Job | |
| total_spend_inr | numeric | |
| total_spend_usd | numeric | |
| top_merchants | JSON | top 3 by spend |
| anomaly_count | int | |
| duplicate_payment_flagged_amount | numeric | total ₹ value of suspected duplicate payments — the "money this tool might have just saved you" number |
| narrative | text | 2-3 sentence plain-language summary, written so a non-technical shop owner understands it |
| risk_level | str | low / medium / high |

### AuditRule (per-business config, optional override of defaults)
| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| business_label | str | |
| outlier_multiplier | float, default 3.0 | flags amount > multiplier × median |
| domestic_only_merchants | JSON array | merchants that should never show foreign currency |
| custom_categories | JSON array, nullable | overrides default category list sent to LLM |

---

## 4. API Endpoints

### `POST /v1/audits/upload`
- Accepts multipart CSV upload + optional `business_label` field.
- Validates: file is CSV, has expected columns.
- Computes `file_hash`; if a completed Job with the same hash + business_label
  already exists, returns that job's id instead of reprocessing (idempotent
  re-upload — prevents double-billing the LLM for an accidental duplicate
  upload, which matters once you're calling a paid-ish API per row).
- Creates `Job` row with `status=pending`.
- Enqueues Celery task with job_id.
- Returns `{job_id}` immediately (HTTP 202).

### `GET /v1/audits/{job_id}/status`
- Returns `{job_id, status, row_count_raw, row_count_clean}`.
- If `status=completed`, also includes a `summary` field (high-level stats from JobSummary).

### `GET /v1/audits/{job_id}/results`
- Returns full structured output:
  - `transactions`: cleaned transaction list
  - `flagged`: anomalous transactions only, grouped by `anomaly_reason`
  - `category_breakdown`: spend per category
  - `narrative_summary`: the LLM JobSummary object

### `GET /v1/audits/{job_id}/export.csv`
- Returns the cleaned + annotated transaction list as a downloadable CSV
  (flags and categories included as extra columns) — this is the artifact a
  business owner actually hands to their CA, so the loop from "messy data in"
  to "usable file out" is closed, not just an API response.

### `POST /v1/audits/{job_id}/retry`
- Re-runs only the failed portion of the pipeline (LLM classification and/or
  narrative generation) for a job where `llm_failed=True` on some rows, without
  reprocessing cleaning/anomaly detection. Real-world LLM calls fail; reprocessing
  a whole job because one API call timed out is wasteful.

### `GET /v1/audits`
- Lists all jobs: `status, filename, business_label, row_count, created_at`.
- Supports `?status=` and `?business_label=` filters (the latter matters once
  this is framed as a multi-client tool for a CA, not single-user).

---

## 5. Processing Pipeline (Celery task, executed in order)

### a) Data Cleaning
- Normalize all dates to ISO 8601 (`YYYY-MM-DD`). Input has mixed `DD-MM-YYYY` and `YYYY/MM/DD`.
- Strip `$`/`₹` prefixes from amounts, cast to numeric.
- Uppercase `status` and `currency` values.
- Fill blank `category` with `'Uncategorised'`.
- Drop exact duplicate rows (identical txn_id + date + amount + merchant — true
  duplicate *records*, distinct from duplicate *payments*, see below).
- Record `row_count_raw` vs `row_count_clean`.

### b) Anomaly Detection
Checked in this priority order (a row keeps only the first reason that applies,
v1 simplification):

1. **Duplicate payment detection** — same `merchant` + same `amount` (±1%) +
   `date` within a 3-day window, on the same `account_id`, but *not* an exact
   duplicate row (different txn_id). This is the highest-value check for the
   target user — it's the one that literally catches money being paid twice.
   → `anomaly_reason = 'duplicate_payment'`, sets `duplicate_of_txn_id`.
2. **Statistical outlier** — per `account_id`, compute median transaction
   amount. Flag any transaction where `amount > outlier_multiplier × median`
   (default 3.0, overridable via `AuditRule`).
   → `anomaly_reason = 'statistical_outlier'`.
3. **Currency mismatch** — `currency == 'USD'` and `merchant` is in the
   business's `domestic_only_merchants` list (default seed: `Swiggy`, `Ola`,
   `IRCTC`).
   → `anomaly_reason = 'currency_mismatch'`.

### c) LLM Classification (batched)
- Collect all transactions where `category == 'Uncategorised'`.
- Send them in **one batched prompt** (not one call per row) asking the LLM to
  return a JSON array mapping `txn_id → category`, where category ∈ the
  business's `custom_categories` if set, else the default list:
  `[Food, Shopping, Travel, Transport, Utilities, Rent, Salaries, Inventory/Supplies, Cash Withdrawal, Other]`
  (default list reframed for a small-business expense context rather than a
  personal-spending one).
- Parse response, update `llm_category` per transaction.
- Wrap the LLM call in `tenacity` retry: 3 attempts, exponential backoff.
- If all 3 retries fail → mark affected transactions `llm_failed=True`, continue
  pipeline (do not fail the whole job). Recoverable later via `/retry`.

### d) LLM Narrative Summary (single call)
- Send aggregated stats (total spend by currency, top merchants, anomaly count,
  flagged duplicate-payment amount) to LLM.
- Request JSON response:
  `{total_spend_by_currency, top_3_merchants, anomaly_count, duplicate_payment_flagged_amount, narrative (2-3 sentences, plain language, no jargon), risk_level}`.
- Prompt explicitly asks for the narrative to be understandable by a
  non-technical shop owner, not an analyst — this is a deliberate product
  decision, not just an LLM call.
- Store as `JobSummary`.
- Same retry logic as (c).

### e) Job completion
- Set `Job.status = completed`, `completed_at = now()`.
- On any unhandled pipeline exception → `Job.status = failed`, `error_message` set.

---

## 6. Non-Functional Requirements

- `docker-compose.yml` must spin up: API service, Celery worker, Redis,
  PostgreSQL — single command, no manual steps (migrations run automatically on
  container start via entrypoint script).
- Healthchecks defined for each service in compose; API/worker `depends_on`
  uses `condition: service_healthy`, not just startup order.
- Structured (JSON) logging across API and worker, including job_id as a
  correlation field, so a failed job can be traced through logs.
- `/metrics` endpoint (Prometheus format) exposing job counts by status and
  LLM call success/failure rates.
- README must include: setup instructions, example `curl` requests for all
  endpoints, sample input CSV, and a note on environment variables
  (`.env.example` provided, real `.env` gitignored).
- Code reasonably typed (Pydantic models for request/response), organized into
  clear modules (not one giant `main.py`).

---

## 7. Deliverables Checklist

- [ ] Public GitHub repo (`ledgerguard` or similar — generic, no assignment-specific naming)
- [ ] README with problem framing, setup, curl examples, sample CSV, architecture diagram embedded
- [ ] High-level architecture diagram (draw.io, public link)
- [ ] CI pipeline (GitHub Actions): lint, test, build Docker image on push
- [ ] `k8s/` folder with example Deployment/Service/HPA manifests + a short
      "how this would run in production" note (not deployed — a documented
      design exercise, see Section 9)
- [ ] Optional: minimal frontend (upload form + polling UI + flagged-transactions
      table) to make the demo tangible for a non-technical reviewer — this
      matters more here than in a generic pipeline project, since the whole
      pitch is "a business owner could actually use this"

---

## 8. Scope Cuts (apply in this order if time-constrained)

1. Skip fancy retry backoff tuning — `tenacity` default exponential backoff is enough.
2. Skip auth entirely for v1 (note in README as a known gap, not silently omitted).
3. Anomaly detection: implement duplicate-payment + statistical-outlier first
   (highest product value); add currency-mismatch only if time remains.
4. Skip `AuditRule` per-business overrides if time-constrained — hardcode
   sensible defaults, mention configurability as "designed for, not yet
   exposed via API" in README.
5. Skip pagination on `/v1/audits` and `/results` unless trivial to add.
6. Do NOT skip: async job queue flow, batched LLM classification, narrative
   summary, duplicate-payment detection, docker compose single-command
   startup, CSV export endpoint. These are what make this a *product* and not
   a generic pipeline demo.

---

## 9. Production Notes (Documented, Not Deployed)

Kubernetes is intentionally **not deployed** for this build — a single-service
+ single-worker setup doesn't need cluster orchestration, and standing one up
just to check a box would be the wrong call at this scale. Instead, the repo
includes example manifests and a short write-up covering:

- Horizontal Pod Autoscaler on the Celery worker keyed off Redis queue depth
  (the actual bottleneck under load, not CPU)
- Separating the LLM-calling worker pool from the cleaning/anomaly-detection
  worker pool, since they have very different latency and failure profiles
- Moving from polling (`GET /status`) to a webhook or WebSocket push once
  there's a real frontend, to avoid clients hammering the API

This is meant to be a talking point about *knowing when not to over-engineer*,
not a deployed system.

---

## 10. Future Extensions (post-v1, if continued as a side project)

- Recurring-vendor detection (subscriptions, rent) split out from one-off anomalies
- Multi-file trend view: month-over-month spend comparison for a returning client
- Slack/WhatsApp webhook to push the narrative summary directly once a job completes
- Per-business custom rule UI instead of editing `AuditRule` rows directly