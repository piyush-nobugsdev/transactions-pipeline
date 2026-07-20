# LedgerGuard — AI-Powered Expense Audit Tool for Small Businesses

**Version 2** — updated with storage, frontend, auth, and retention decisions.

---

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
| File Storage | **AWS S3** | Durable, cheap object storage for raw CSV uploads; decoupled from app servers |
| Frontend | **React (Vite, minimal)** | Signals full-stack literacy for portfolio purposes; makes the demo tangible for a non-technical reviewer |
| Containerization | **Docker + Docker Compose** | Single-command startup required |
| Data cleaning | **pandas** | Fast for CSV normalization |
| Retry logic | **tenacity** | Decorator-based retries with exponential backoff, minimal code |
| CI | **GitHub Actions** | Lint, test, build Docker image on push |

---

## 3. AWS S3 — Primer (You're New to This, So Here's the Mental Model)

S3 is **object storage**, not a filesystem and not a database. Think of it as a
giant, infinitely scalable key-value store where the "value" is a file (an
"object") and the "key" is just a string path you make up.

**Core concepts:**

- **Bucket** — a top-level container, globally unique name across all of AWS
  (e.g. `ledgerguard-uploads-prod`). You'll have one bucket, maybe two
  (uploads vs exports) for this project.
- **Key** — the full "path" to an object inside a bucket. There are no real
  folders in S3 — `businesses/acme-traders/2026/07/16/statement.csv` is just
  one long string used as the key. The AWS console *displays* it like folders,
  but it's cosmetic.
- **Object** — the actual file bytes, plus metadata (content-type, size,
  custom tags like `job_id`).
- **Region** — pick one close to your users (`ap-south-1` = Mumbai, makes
  sense given your context) and stick with it. Cross-region access adds
  latency and sometimes cost.

**How your app will talk to S3:**

1. Your FastAPI service receives the multipart upload from the client.
2. It uploads the file bytes to S3 using the **boto3** SDK (`s3_client.upload_fileobj(...)`).
3. S3 returns nothing exciting on success — you just store the **key** you
   chose (e.g. `job_id/original.csv`) in your `Job` row.
4. Later, to read the file back (e.g. in the Celery worker), you call
   `s3_client.get_object(Bucket=..., Key=...)` and stream it into pandas.

**Access control — the part people get wrong:**

- Your bucket should be **private** (Block Public Access = ON, all four
  settings). Nobody should be able to guess a URL and download someone else's
  bank statement.
- Your FastAPI/Celery containers authenticate to S3 via an **IAM role**
  (if deployed on AWS — e.g. an EC2 instance role or ECS task role) or, for
  local dev, an IAM user's access key/secret in your `.env` (never committed —
  matches your existing `.env.example` convention).
- The IAM policy attached should be scoped to *only* that bucket and only the
  actions you need (`s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`) — not
  `s3:*` on `*`. This is a good "I understand least-privilege" talking point.

**Encryption:** turn on **SSE-S3** (server-side encryption, AES-256) at the
bucket level. It's a single checkbox/config flag, AWS manages the keys, and
it's the correct default for anything containing financial data. You don't
need KMS (customer-managed keys) for a project at this scale — that's the
kind of over-engineering call worth explicitly *not* making, similar to your
Kubernetes decision in Section 9.

**Presigned URLs (good to know, not required for v1):** S3 supports
generating a temporary, signed URL that lets a client upload or download
directly to/from S3 without the request passing through your API server at
all. This is the "real" production pattern for large files, since it avoids
tying up your FastAPI worker processes with file transfer. For this project,
your CSVs are small enough that routing the upload through FastAPI (as
already specced) is simpler and totally fine — but you should be able to say
*why* you didn't need presigned URLs here, not that you didn't know about them.

**Lifecycle policies:** a bucket-level rule that automatically deletes (or
archives) objects after N days, with no code required. This is how you'll
implement data retention (see Section 7).

---

## 4. Data Model

### Job (one per uploaded statement/export)
| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| filename | str | original filename as uploaded |
| business_label | str, nullable | optional client/shop name for multi-client use (e.g. a CA running this for several clients) |
| status | enum | `pending`, `processing`, `completed`, `failed` |
| file_hash | str | SHA-256 of raw upload, used for idempotent re-upload detection |
| **s3_bucket** | str | **NEW** — bucket the raw upload lives in |
| **s3_key** | str | **NEW** — e.g. `{job_id}/original.csv` |
| **file_size_bytes** | int | **NEW** — enforced against max-size cap at upload time |
| **content_type** | str | **NEW** — should always be `text/csv`, validated |
| row_count_raw | int | |
| row_count_clean | int | |
| created_at | datetime | |
| completed_at | datetime, nullable | |
| **expires_at** | datetime | **NEW** — `created_at + retention_days`, mirrors the S3 lifecycle rule so the DB and the bucket agree on when data disappears |
| error_message | str, nullable | |

**Decision: fields on `Job`, not a separate table.** The relationship between
a Job and its raw upload is 1:1 today, so a join-only-table adds overhead
without benefit. **Ideal/future path:** once there's more than one artifact
per job — e.g. you start storing the generated `/export.csv` in S3 too instead
of regenerating it on each request — introduce a `JobArtifact(job_id,
artifact_type, s3_bucket, s3_key, created_at)` table. That's the point where
a separate table earns its complexity: one row per file, extensible to future
artifact types (PDF report, etc.) without more columns on `Job`.

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
| **retention_days** | int, default 30 | **NEW** — how long this business's data is kept before deletion |

### BusinessApiKey (optional, "auth-lite" — see Section 6)
| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| business_label | str | |
| api_key_hash | str | store a hash, never the raw key |
| created_at | datetime | |
| revoked_at | datetime, nullable | |

---

## 5. API Endpoints

### `POST /v1/audits/upload`
- Accepts multipart CSV upload + optional `business_label` field.
- Validates: file is CSV, has expected columns, **size ≤ cap (e.g. 5MB), row
  count ≤ cap** (NEW — prevents unbounded Celery task time and unbounded LLM
  cost from a runaway or malicious upload).
- Computes `file_hash`; if a completed Job with the same hash + business_label
  already exists, returns that job's id instead of reprocessing (idempotent
  re-upload — prevents double-billing the LLM for an accidental duplicate
  upload).
- Uploads raw file to S3 (`s3_key = {job_id}/original.csv`), stores
  `s3_bucket`, `s3_key`, `file_size_bytes`, `content_type` on the Job row.
- Sets `expires_at = now() + retention_days` (from `AuditRule` if set, else default 30).
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
  (flags and categories included as extra columns).

### `POST /v1/audits/{job_id}/retry`
- Re-runs only the failed portion of the pipeline (LLM classification and/or
  narrative generation) for a job where `llm_failed=True` on some rows.

### `GET /v1/audits`
- Lists all jobs: `status, filename, business_label, row_count, created_at`.
- Supports `?status=` and `?business_label=` filters.

### `DELETE /v1/audits/{job_id}` — **NEW**
- Deletes the Job, its Transactions, its JobSummary, **and** the S3 object(s).
- Needed regardless of the lifecycle policy, for explicit user-initiated
  deletion (a real trust feature for a tool handling financial data — "delete
  my data" should be one call away, not just a 30-day wait).

---

## 6. Auth — Decision

**v1: no login/signup.** This was already the right call in the original scope
cut, and it still is — a User table, JWT issuance, and per-request ownership
checks is multiple days of work on its own and doesn't demonstrate anything
about the actual pipeline this project exists to show off. Document it in the
README as a known, deliberate gap.

**Tenant identification without auth:** `business_label` is a free-text field,
not a security boundary — it lets you filter/group jobs per client (useful
for the CA-with-15-clients use case) without pretending it's access control.

**Optional middle ground ("auth-lite"), if you want one without full auth
complexity:** a per-business API key, sent as a header (`X-API-Key`), checked
against `BusinessApiKey.api_key_hash`. This gives you a real security boundary
— someone can't list or delete another business's jobs — for a fraction of
the build cost of full login/signup, and it's a good story for an interview:
you can explain the trade-off between "no auth," "API key," and "full
JWT-based auth" and why you picked the middle one (or didn't).

---

## 7. Data Retention — Decision

Given this is bank/UPI transaction data, retention deserves a real answer even
in a demo project.

- **Default: 30 days**, configurable per business via `AuditRule.retention_days`.
- Implemented via an **S3 Lifecycle Policy** on the bucket (a rule you
  configure once, no cron job or scheduled task needed — S3 handles expiry
  itself).
- `Job.expires_at` is set on upload to mirror the lifecycle rule, so the
  database and the bucket agree, and so a nightly cleanup job (or a
  scheduled Celery beat task) can also null out/soft-delete the DB rows
  once `expires_at` has passed, keeping Postgres from accumulating orphaned
  metadata for objects that no longer exist in S3.
- The `DELETE` endpoint (Section 5) exists for immediate, user-initiated
  deletion, independent of the 30-day default.
- Worth a line in the README: "uploaded statements are automatically deleted
  after 30 days" is a genuine trust signal for a CA-facing tool, not just an
  implementation detail.

---

## 8. Frontend — Decision

**React (Vite, no framework beyond that — no Next.js, no Redux).** Three
screens are enough:

1. **Upload form** — file input + optional `business_label` field, hits
   `POST /v1/audits/upload`.
2. **Status view** — polls `GET /v1/audits/{job_id}/status` until `completed`.
3. **Results view** — flagged-transactions table (grouped by
   `anomaly_reason`), category breakdown, narrative summary, and a download
   link for `/export.csv`.

Rationale: this is a portfolio project meant to demonstrate you can ship a
usable product, not just a pipeline — a real (if minimal) frontend makes the
demo tangible for a non-technical reviewer, which matters more here than in a
generic backend-only project. A Streamlit/Gradio frontend would be faster to
build but reads as an internal tool rather than a product; use it only as a
fallback if you're genuinely out of time, and be ready to explain that
trade-off rather than present it as the ideal choice.

**Don't forget CORS** — once the frontend runs on a different origin/port
than FastAPI, you'll need `CORSMiddleware` configured (allowed origins,
methods, headers) or the first demo attempt will just be a browser console
error.

---

## 9. Processing Pipeline (Celery task, executed in order)

### a) Data Cleaning
- Normalize all dates to ISO 8601 (`YYYY-MM-DD`). Input has mixed `DD-MM-YYYY` and `YYYY/MM/DD`.
- Strip `$`/`₹` prefixes from amounts, cast to numeric.
- Uppercase `status` and `currency` values.
- Fill blank `category` with `'Uncategorised'`.
- Drop exact duplicate rows (identical txn_id + date + amount + merchant).
- Record `row_count_raw` vs `row_count_clean`.

### b) Anomaly Detection
Checked in this priority order (a row keeps only the first reason that applies,
v1 simplification):

1. **Duplicate payment detection** — same `merchant` + same `amount` (±1%) +
   `date` within a 3-day window, on the same `account_id`, but *not* an exact
   duplicate row (different txn_id).
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
- Send them in **one batched prompt** asking the LLM to return a JSON array
  mapping `txn_id → category`, category ∈ `custom_categories` if set, else:
  `[Food, Shopping, Travel, Transport, Utilities, Rent, Salaries, Inventory/Supplies, Cash Withdrawal, Other]`.
- Parse response, update `llm_category` per transaction.
- Wrap the LLM call in `tenacity` retry: 3 attempts, exponential backoff.
- If all 3 retries fail → mark affected transactions `llm_failed=True`,
  continue pipeline. Recoverable later via `/retry`.

### d) LLM Narrative Summary (single call)
- Send aggregated stats to LLM, request JSON response:
  `{total_spend_by_currency, top_3_merchants, anomaly_count, duplicate_payment_flagged_amount, narrative (2-3 sentences, plain language, no jargon), risk_level}`.
- Store as `JobSummary`. Same retry logic as (c).

### e) Job completion
- Set `Job.status = completed`, `completed_at = now()`.
- On any unhandled pipeline exception → `Job.status = failed`, `error_message` set.

---

## 10. Non-Functional Requirements

- `docker-compose.yml` must spin up: API service, Celery worker, Redis,
  PostgreSQL — single command, migrations run automatically on container
  start via entrypoint script.
- Healthchecks defined for each service; `depends_on` uses
  `condition: service_healthy`.
- Structured (JSON) logging across API and worker, including `job_id` as a
  correlation field.
- `/metrics` endpoint (Prometheus format): job counts by status, LLM call
  success/failure rates.
- **Rate limiting on `/upload`** (NEW) — per-IP or per-`business_label`,
  since without auth nothing else stops repeated uploads from burning LLM
  quota.
- README must include: setup instructions, example `curl` requests for all
  endpoints, sample input CSV, architecture diagram, environment variables
  (`.env.example` provided, real `.env` gitignored — including AWS
  credentials/region/bucket name), and the retention policy statement.
- Code reasonably typed (Pydantic models), organized into clear modules.

---

## 11. Deliverables Checklist

- [ ] Public GitHub repo (`ledgerguard` or similar)
- [ ] README with problem framing, setup, curl examples, sample CSV,
      architecture diagram embedded, retention policy note
- [ ] High-level architecture diagram (draw.io, public link) — should now
      show S3 and the React frontend alongside the existing components
- [ ] CI pipeline (GitHub Actions): lint, test, build Docker image on push
- [ ] `k8s/` folder with example Deployment/Service/HPA manifests + short
      "how this would run in production" note (not deployed)
- [ ] Minimal React frontend (upload form + polling UI + flagged-transactions
      table + export download link)

---

## 12. Scope Cuts (apply in this order if time-constrained)

1. Skip fancy retry backoff tuning — `tenacity` default is enough.
2. Skip auth/API-key entirely for v1 (documented gap); rely on `business_label` only.
3. Anomaly detection: duplicate-payment + statistical-outlier first; add
   currency-mismatch only if time remains.
4. Skip `AuditRule` per-business overrides if time-constrained — hardcode
   defaults, note configurability as "designed for, not yet exposed."
5. Skip pagination on `/v1/audits` and `/results` unless trivial.
6. Skip the `JobArtifact` table refactor — fields on `Job` are sufficient for v1.
7. **Do NOT skip:** async job queue flow, batched LLM classification,
   narrative summary, duplicate-payment detection, docker compose
   single-command startup, CSV export endpoint, S3 upload/retrieval,
   `DELETE` endpoint, file size/row caps. These are what make this a
   *product* and not a generic pipeline demo — or, in the new items' case,
   what make it a *responsible* product handling financial data.

---

## 13. Production Notes (Documented, Not Deployed)

Kubernetes is intentionally **not deployed** — a single-service + single-worker
setup doesn't need cluster orchestration at this scale. The repo includes
example manifests and a short write-up covering:

- Horizontal Pod Autoscaler on the Celery worker keyed off Redis queue depth
- Separating the LLM-calling worker pool from the cleaning/anomaly-detection
  worker pool (different latency/failure profiles)
- Moving from polling to a webhook or WebSocket push once there's a real
  frontend under load
- **Presigned S3 URLs** (NEW) — the production-scale answer for large-file
  uploads, letting the client talk to S3 directly instead of routing bytes
  through FastAPI. Not needed at this project's file sizes, documented as a
  deliberate non-choice like the Kubernetes decision above.

This is meant to be a talking point about *knowing when not to over-engineer*,
not a deployed system.

---

## 14. Future Extensions (post-v1, if continued as a side project)

- Recurring-vendor detection (subscriptions, rent) split out from one-off anomalies
- Multi-file trend view: month-over-month spend comparison for a returning client
- Slack/WhatsApp webhook to push the narrative summary directly once a job completes
- Per-business custom rule UI instead of editing `AuditRule` rows directly
- `JobArtifact` table once more than one file type per job exists
- Full auth (JWT-based) if this ever moves beyond a portfolio piece
