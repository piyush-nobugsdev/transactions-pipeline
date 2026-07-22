# LedgerGuard Backend Implementation Plan

> **Purpose:** This document is the working master plan for building the LedgerGuard backend in a deliberate, modular, production-quality way.
>
> **Important architectural rule:** This document intentionally does **not** make final architectural decisions on behalf of the developer. Where the implementation requires a decision, the decision is explicitly marked for the human developer to make. Best-practice recommendations are provided as guidance only.

---

# 1. Project Context

LedgerGuard is an AI-powered expense audit tool for small businesses and CAs.

The core flow described in the PRD is:

```text
User uploads CSV
       |
       v
FastAPI receives upload
       |
       v
Validate file
       |
       v
Create audit/job record
       |
       v
Store raw CSV in S3
       |
       v
Dispatch asynchronous processing job
       |
       v
Celery + Redis
       |
       v
Worker processes the job
       |
       +--> Data cleaning
       |
       +--> Anomaly detection
       |
       +--> LLM classification
       |
       +--> LLM narrative summary
       |
       v
Persist results
       |
       v
Mark job completed
       |
       v
Client polls status
       |
       v
Client retrieves results / exports CSV
```

The PRD defines the following major technology choices:

- FastAPI
- PostgreSQL
- SQLAlchemy 2.0 async
- Alembic
- Celery + Redis
- Gemini 1.5 Flash
- AWS S3
- React + Vite
- Docker + Docker Compose
- pandas
- tenacity
- GitHub Actions

The PRD also requires:

- structured JSON logging
- `job_id` as a correlation field
- `/metrics` in Prometheus format
- rate limiting on `/upload`
- healthchecks
- automatic database migrations on container startup
- data retention
- explicit deletion
- a minimal React frontend
- CI
- example Kubernetes manifests/documentation

This plan separates the work into:

1. Core/cross-cutting infrastructure
2. Business/domain modules
3. Implementation order
4. Human architectural decisions
5. Definition of done

---

# 2. Current Foundation Status

At the time this plan was created, the following cross-cutting concerns are considered complete:

| Concern | Status |
|---|---|
| Environment/configuration validation | Complete |
| Centralized exception handling | Complete |

These should be treated as existing foundations rather than rebuilt unnecessarily.

The remaining foundational work should be evaluated against the repository's current implementation and `AGENTS.md` before coding.

---

# 3. Architectural Philosophy

The intended high-level separation is:

```text
                         LedgerGuard
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
      Cross-Cutting/Core                 Business Modules
             |                                 |
     +-------+-------+                 +-------+-------+
     |       |       |                 |       |       |
   Config  Database Storage           Audits Transactions
     |       |       |                 |       |
 Exceptions Logging Queue             Processing
     |       |       |                 |
 Health  Metrics  Security             +--------+--------+
                                       |                 |
                                  Anomalies             AI
```

The key distinction is:

### Core/cross-cutting concerns

These provide capabilities used by multiple parts of the application.

Examples:

- configuration
- exception handling
- logging
- database access
- object storage
- background queue
- health checks
- metrics
- rate limiting
- CORS/security

### Business modules

These represent LedgerGuard's actual domain behavior.

Examples:

- audits/jobs
- transactions
- processing
- anomaly detection
- AI/LLM functionality

Do not automatically create a module for every technology.

For example:

- S3 is infrastructure, not a business module.
- Redis is infrastructure, not a business module.
- Celery is infrastructure, not a business module.
- PostgreSQL is infrastructure, not a business module.
- Gemini is an external provider used through an AI/LLM abstraction.

---

# 4. CORE / CROSS-CUTTING CONCERNS

## 4.1 Configuration and Environment Validation

### Status

Complete.

### Responsibility

The configuration layer is responsible for:

- loading environment variables
- validating required configuration
- providing typed configuration values
- preventing invalid application startup
- centralizing configuration access

Potential configuration areas include:

- database URL
- Redis URL
- Celery configuration
- AWS region
- S3 bucket
- AWS credentials for local development
- Gemini API configuration
- upload size limits
- row limits
- retention defaults
- CORS origins
- rate-limit configuration
- logging configuration

### Implementation guidance

The existing configuration implementation should remain the source of truth.

Future modules should consume configuration through the established configuration mechanism rather than reading `os.environ` directly.

Avoid:

```python
os.getenv("DATABASE_URL")
```

throughout business code.

Prefer the project's centralized configuration object.

### Human decisions

The following decisions remain for the developer:

- Which configuration values are mandatory?
- Which have safe defaults?
- Which configuration values differ between local, test, and production environments?
- Which secrets are loaded from environment variables versus deployment secret managers?
- How should configuration be grouped?

### Best-practice recommendation

Keep configuration centralized, typed, validated at startup, and independent from business modules.

---

## 4.2 Centralized Exception Handling

### Status

Complete.

### Responsibility

The exception system should provide:

- application exception hierarchy
- consistent API error responses
- global FastAPI exception handlers
- unexpected exception handling
- safe error responses
- internal logging of unexpected failures
- separation between application errors and HTTP transport concerns

The desired conceptual flow is:

```text
Service / Domain
      |
      v
Application Exception
      |
      v
FastAPI Exception Adapter
      |
      v
HTTP Response
```

Infrastructure exceptions may be translated at appropriate boundaries:

```text
Database / S3 / External API Error
      |
      v
Infrastructure Boundary
      |
      v
Application Exception
      |
      v
Global Exception Handler
```

### Important rule

Centralized handling does not mean eliminating all `try/except`.

Use `try/except` when:

- translating a low-level exception
- retrying an operation
- performing compensation/recovery
- adding meaningful context
- handling a known local failure

Avoid repetitive route-level patterns such as:

```python
try:
    ...
except AppException:
    return JSONResponse(...)
```

when the global handler already handles the exception.

### Human decisions

- Exact exception hierarchy
- Error response schema
- Which errors are exposed to clients
- Which infrastructure errors are translated
- Logging levels for expected errors
- Whether any environment-specific error detail is exposed

### Best-practice recommendation

Keep business logic independent from FastAPI-specific `HTTPException` where practical.

---

## 4.3 Structured Logging and Correlation

### Status

Recommended next foundational concern.

### Why it is required

LedgerGuard is asynchronous and distributed across:

```text
FastAPI
PostgreSQL
Redis
Celery
S3
LLM provider
```

When a job fails, logs need to answer:

- Which job failed?
- Which processing stage failed?
- Which request initiated the job?
- Which worker processed it?
- What was the exception?
- How long did the stage take?

The PRD explicitly requires structured JSON logging with `job_id` as a correlation field.

### Responsibilities

The logging layer should provide:

- structured JSON logs
- consistent fields
- log levels
- exception tracebacks
- `job_id` correlation
- request correlation if implemented
- safe logging without secrets

Example conceptual log:

```json
{
  "timestamp": "2026-07-22T10:00:00Z",
  "level": "ERROR",
  "event": "job_processing_failed",
  "job_id": "abc-123",
  "stage": "llm_classification",
  "error_code": "LLM_TIMEOUT"
}
```

### Implementation considerations

Potential structure:

```text
core/
└── logging/
    ├── configuration.py
    ├── formatters.py
    └── context.py
```

The exact structure must follow `AGENTS.md` and existing repository conventions.

The logging system should work for both:

- FastAPI processes
- Celery workers

### Human decisions

- Logging library
- JSON formatter implementation
- Exact correlation ID strategy
- Whether `job_id` is sufficient or whether a separate `request_id`/trace ID is required
- Which fields are mandatory
- Log retention and aggregation platform
- Whether sensitive data should be redacted automatically

### Best-practice recommendation

At minimum, ensure `job_id` appears in all logs generated during asynchronous processing.

Do not log:

- API keys
- passwords
- access tokens
- AWS secrets
- database credentials
- Authorization headers
- sensitive financial data unnecessarily

---

## 4.4 Database Infrastructure

### Status

Recommended next foundational concern.

### Technology

The PRD specifies:

- PostgreSQL
- SQLAlchemy 2.0 async
- Alembic

### Responsibility

The database infrastructure should provide:

- SQLAlchemy engine
- async session factory
- declarative base
- session lifecycle
- dependency integration
- transaction management conventions
- model registration
- database connectivity

Conceptual flow:

```text
FastAPI Request
      |
      v
Dependency Injection
      |
      v
AsyncSession
      |
      v
Repository
      |
      v
PostgreSQL
```

Celery workers will also need controlled database access.

### Potential structure

```text
core/
└── database/
    ├── base.py
    ├── session.py
    └── models/
```

The exact structure is a human architectural decision.

### Important design questions

The project must decide:

- Who owns database commits?
- Who owns rollbacks?
- Are repositories responsible for persistence only?
- Are services responsible for transaction boundaries?
- How are transactions handled across multiple repositories?
- How are worker sessions created?
- How are database exceptions translated?

### Best-practice recommendation

Establish one clear transaction ownership rule and apply it consistently.

Avoid having both repositories and services unpredictably call `commit()`.

---

## 4.5 Alembic Migrations

### Status

Recommended before creating production data models.

### Responsibility

Alembic manages:

- database schema evolution
- migration history
- reproducible database setup
- deployment schema upgrades

Conceptual flow:

```text
SQLAlchemy Model Change
        |
        v
Alembic Migration
        |
        v
Git Commit
        |
        v
Deployment
        |
        v
Database Upgrade
```

The PRD requires migrations to run automatically during container startup.

### Human decisions

- Exact migration execution strategy
- Whether migrations run in an API entrypoint
- Whether a dedicated migration container/service is used
- How production migration locking is handled
- Whether migrations are always automatic or manually triggered in production

### Best-practice recommendation

Avoid having multiple application replicas independently attempt migrations at the same time.

---

## 4.6 Dependency Injection

### Status

The project should establish and document its pattern before modules grow.

### Responsibility

DI should provide dependencies such as:

- database sessions
- repositories
- services
- storage
- queue dispatcher
- LLM clients

Conceptual flow:

```text
Router
   |
   v
Service
   |
   +--> Repository
   |
   +--> Storage
   |
   +--> Queue
```

### Human decisions

- Constructor injection versus FastAPI `Depends`
- Where dependency providers live
- Whether services are instantiated per request
- How Celery dependencies are constructed
- Whether interfaces/protocols are used for external dependencies

### Best-practice recommendation

Use FastAPI's dependency injection where it naturally fits HTTP request handling and use constructor-based composition for services where practical.

Avoid a large dependency-injection framework unless the project actually needs one.

---

## 4.7 Storage Abstraction

### Status

Recommended before the Upload/Audit module.

### Technology

AWS S3.

### Responsibility

Provide a stable application-facing interface for:

- upload
- download
- delete
- existence checks if needed
- metadata if needed

Conceptual architecture:

```text
Business Module
      |
      v
Storage Interface
      |
      v
S3 Adapter
      |
      v
AWS S3
```

Potential conceptual interface:

```python
upload(...)
download(...)
delete(...)
```

### Why it matters

It prevents S3-specific code from spreading through:

- upload logic
- processing logic
- deletion logic
- export logic

It also improves testing.

Production:

```text
S3Storage
```

Tests:

```text
FakeStorage / MockStorage
```

### Human decisions

- Interface shape
- Whether storage is synchronous or async at the application boundary
- Whether files are streamed or fully loaded
- S3 client lifecycle
- Bucket strategy
- S3 key naming strategy
- Whether one bucket or multiple buckets are used
- Whether presigned URLs are introduced now or documented for later

### PRD guidance

The PRD currently specifies routing uploads through FastAPI for v1 and documents presigned URLs as a future production-scale option.

Do not change this decision automatically; treat it as a human-controlled architectural decision.

---

## 4.8 Queue / Background Job Infrastructure

### Status

Recommended before the Processing module.

### Technology

Celery + Redis.

### Responsibility

Provide:

- Celery application configuration
- broker configuration
- task dispatching
- task registration
- worker configuration
- retry/error behavior foundation

Conceptual architecture:

```text
FastAPI
   |
   v
Queue Dispatcher
   |
   v
Celery
   |
   v
Redis
   |
   v
Worker
```

The business processing module should define what the worker does.

The infrastructure layer should define how Celery works.

### Human decisions

- Celery task naming conventions
- Retry strategy
- Acknowledgement behavior
- Worker concurrency
- Queue naming
- Whether multiple queues are used
- Whether cleaning and LLM workloads use separate workers
- Celery Beat usage for retention cleanup
- Task idempotency strategy

### Best-practice recommendation

Keep queue infrastructure separate from business processing logic.

---

## 4.9 Health and Readiness

### Status

Recommended before integration testing and deployment.

### Responsibility

Provide health endpoints and container health checks.

Conceptual separation:

```text
/health
    |
    +--> Process is alive

/ready
    |
    +--> Dependencies are available
```

Potential readiness checks:

- PostgreSQL
- Redis

### Human decisions

- Exact endpoint names
- Which dependencies are checked
- Whether S3 is included
- Whether Gemini is included
- Whether health and readiness are separate

### Best-practice recommendation

Do not make a basic liveness endpoint depend on external services.

---

## 4.10 CORS

### Status

Required before frontend integration.

### Responsibility

Allow the React frontend to communicate with FastAPI when running on a different origin.

Configuration should be environment-driven.

### Human decisions

- Allowed origins
- Allowed methods
- Allowed headers
- Whether credentials are allowed

### Best-practice recommendation

Do not use unrestricted `*` origins in a production configuration.

---

## 4.11 Metrics

### Status

Required by the PRD; implementation can be incremental.

### Responsibility

Expose:

```text
GET /metrics
```

in Prometheus format.

The PRD specifically requires metrics for:

- job counts by status
- LLM call success/failure rates

Potential metrics:

```text
jobs_total
jobs_completed_total
jobs_failed_total
llm_calls_total
llm_calls_success_total
llm_calls_failed_total
```

### Human decisions

- Metrics library
- Metric names
- Labels
- Histogram requirements
- Whether HTTP metrics are included
- Whether Celery worker metrics are exposed

### Best-practice recommendation

Build the metrics infrastructure early but add business metrics alongside the modules that generate them.

---

## 4.12 Rate Limiting

### Status

Required by the PRD for `/upload`.

### Why it matters

v1 intentionally has no full authentication.

Therefore, unrestricted upload access could cause:

- repeated processing
- excessive LLM usage
- resource exhaustion
- abuse

### Potential strategy

```text
Request
   |
   v
Rate Limiter
   |
   v
Upload
```

Possible keys:

- IP address
- business identity
- API key

### Human decisions

- Whether rate limiting is per-IP
- Whether it is per-business
- Whether API keys are introduced
- Rate limits
- Time windows
- Redis-backed implementation
- Behavior when the limit is exceeded

### Best-practice recommendation

Use Redis if rate limiting needs to work consistently across multiple API instances.

---

## 4.13 Security / Authentication Boundary

### Status

The PRD explicitly chooses no full login/signup for v1.

The PRD describes an optional API-key approach.

This must remain a human decision.

### Human decisions

- No auth
- Auth-lite API keys
- Full authentication
- When authentication becomes necessary
- Business ownership/security boundaries

### Important distinction

`business_label` is not a security boundary.

It must not be treated as authorization.

### Best-practice recommendation

If the service becomes publicly accessible or handles real users' financial data, revisit authentication and authorization before production use.

---

# 5. BUSINESS MODULES

The recommended business/domain decomposition is **five core modules**.

These are:

1. Audits / Jobs
2. Transactions
3. Processing
4. Anomaly Detection
5. AI / LLM

This is a recommended decomposition, not a final architectural decision.

The developer should validate it against `AGENTS.md` and the actual evolving codebase.

---

# 6. Business Module 1 — Audits / Jobs

## Purpose

This should represent the primary business workflow of LedgerGuard.

The central concept is an audit job.

The upload is an entry point into an audit, not necessarily the entire business concept.

## Responsibilities

The module owns the audit/job lifecycle:

```text
pending
   |
   v
processing
   |
   +----> failed
   |
   v
completed
```

It is responsible for:

- creating jobs
- validating job-level input
- storing job metadata
- retrieving job status
- listing jobs
- retrieving results
- retrying failed work
- deleting jobs
- initiating processing

## PRD endpoints

Potentially:

```text
POST   /v1/audits/upload
GET    /v1/audits/{job_id}/status
GET    /v1/audits/{job_id}/results
GET    /v1/audits/{job_id}/export.csv
POST   /v1/audits/{job_id}/retry
GET    /v1/audits
DELETE /v1/audits/{job_id}
```

## Data

Primary entity:

```text
Job
```

Associated result:

```text
JobSummary
```

## Implementation concept

```text
Audit Router
      |
      v
Audit Service
      |
      +--> Job Repository
      |
      +--> Storage
      |
      +--> Queue Dispatcher
      |
      +--> Audit Rule Configuration
```

The Audit module should orchestrate the workflow without implementing the actual data-cleaning or anomaly algorithms.

## Human decisions

- Exact module boundaries
- Whether `JobSummary` belongs to Audits or another module
- Whether upload belongs inside Audits or a separate Upload module
- Where export generation belongs
- Where retry orchestration belongs
- Whether job lifecycle state transitions are enforced in a dedicated service

## Best-practice recommendation

Treat `Job` as the central aggregate/workflow entity and keep processing algorithms outside the Audit module.

---

# 7. Business Module 2 — Transactions

## Purpose

Own the normalized transaction domain.

## Responsibilities

- transaction persistence
- bulk transaction creation
- transaction retrieval
- transaction querying
- transaction result serialization
- transaction export data preparation

## Data

Primary entity:

```text
Transaction
```

Fields from the PRD include:

- id
- job_id
- txn_id
- date
- merchant
- amount
- currency
- status
- category
- account_id
- is_anomaly
- anomaly_reason
- duplicate_of_txn_id
- llm_category
- llm_raw_response
- llm_failed

## Implementation concept

```text
Processing
    |
    v
Transaction Service
    |
    v
Transaction Repository
    |
    v
PostgreSQL
```

The module should not know about:

- S3 internals
- Celery internals
- HTTP response serialization details
- Gemini API details

## Human decisions

- Whether Transaction is its own module
- Whether processing writes directly through repositories
- Whether transaction mutations are exposed through public APIs
- Whether transaction results are owned by Audits
- How transaction bulk insertion is implemented

## Best-practice recommendation

Keep transaction persistence and domain behavior separate from the pipeline orchestration.

---

# 8. Business Module 3 — Processing

## Purpose

Orchestrate the asynchronous audit pipeline.

The PRD specifies this sequence:

```text
Data Cleaning
     |
     v
Anomaly Detection
     |
     v
LLM Classification
     |
     v
LLM Narrative Summary
     |
     v
Job Completion
```

## Responsibilities

- Celery task orchestration
- job state transitions
- retrieving raw input
- invoking cleaning
- invoking anomaly detection
- invoking classification
- invoking summary generation
- handling recoverable failures
- marking jobs completed/failed
- recording processing errors

## Important distinction

Processing is an orchestrator.

It should not become a giant module containing all business algorithms.

Conceptually:

```text
Processing
   |
   +--> Cleaning
   |
   +--> Anomaly Detection
   |
   +--> AI Classification
   |
   +--> AI Summary
```

## Human decisions

- Whether cleaning gets its own module
- Whether Processing directly orchestrates all stages
- Whether each stage is one Celery task or a single pipeline task
- Whether failed stages can resume independently
- How job state transitions are enforced
- Whether retries happen at Celery level, application level, or both

## Best-practice recommendation

Start with a clear pipeline orchestration layer and avoid over-fragmenting the task graph until there is a real need.

---

# 9. Business Module 4 — Anomaly Detection

## Purpose

Detect suspicious or unusual transactions.

The PRD specifies three v1 rules.

### 1. Duplicate payment

Criteria:

- same merchant
- same amount within ±1%
- date within 3 days
- same account
- not an exact duplicate row

Output:

```text
anomaly_reason = duplicate_payment
duplicate_of_txn_id = ...
```

### 2. Statistical outlier

Per account:

```text
median transaction amount
```

Flag:

```text
amount > outlier_multiplier * median
```

Default multiplier:

```text
3.0
```

### 3. Currency mismatch

Example:

```text
USD transaction
+
domestic-only merchant
```

Output:

```text
anomaly_reason = currency_mismatch
```

## Implementation concept

```text
Processing
    |
    v
Anomaly Detection Service
    |
    +--> Duplicate Detector
    |
    +--> Statistical Outlier Detector
    |
    +--> Currency Mismatch Detector
```

The PRD says a row keeps only the first reason that applies in v1.

The implementation must preserve this priority if that remains the chosen product behavior:

```text
Duplicate
   |
   v
Outlier
   |
   v
Currency mismatch
```

## Human decisions

- Whether all three rules are implemented in v1
- Whether anomaly detectors are separate classes/components
- Exact duplicate matching behavior
- Currency mismatch merchant configuration
- Whether multiple anomaly reasons should eventually be supported
- How anomaly rules are configured
- Whether `AuditRule` is implemented now

## Best-practice recommendation

Keep each detector independently testable.

---

# 10. Business Module 5 — AI / LLM

## Purpose

Provide AI-powered classification and narrative generation.

The PRD specifies:

1. Batched transaction classification
2. Narrative summary generation

## Classification

Input:

```text
Uncategorised transactions
```

Output:

```text
txn_id -> category
```

Default categories:

```text
Food
Shopping
Travel
Transport
Utilities
Rent
Salaries
Inventory/Supplies
Cash Withdrawal
Other
```

## Narrative summary

The LLM should produce:

```text
total_spend_by_currency
top_3_merchants
anomaly_count
duplicate_payment_flagged_amount
narrative
risk_level
```

## Responsibilities

- prompt construction
- batching
- LLM API calls
- retry behavior
- response parsing
- response validation
- category validation
- failure handling
- raw response persistence if required
- summary generation

## External provider boundary

A recommended conceptual architecture:

```text
AI Module
    |
    v
LLM Client Interface
    |
    v
Gemini Adapter
```

This allows future providers or test doubles.

## Retry

The PRD specifies:

- tenacity
- 3 attempts
- exponential backoff

The implementation must ensure failed classification can be recovered through `/retry`.

## Human decisions

- Exact LLM client abstraction
- Gemini SDK choice
- Prompt structure
- Maximum batch size
- Token limits
- Response validation strategy
- Whether raw LLM responses are stored
- Whether LLM failures fail the entire job
- Whether classification and summary are separate tasks
- Retry configuration
- Fallback behavior

## Best-practice recommendation

Treat LLM output as untrusted external input.

Always validate and parse it before persisting it as trusted application data.

---

# 11. Supporting Concepts That Are Not Necessarily Separate Business Modules

## AuditRule

The PRD defines:

- outlier multiplier
- domestic-only merchants
- custom categories
- retention days

This does not necessarily require a top-level business module.

It could be part of:

```text
Audits
```

or a configuration/rules subcomponent.

### Human decision

Decide whether AuditRule is:

- implemented in v1
- stored in PostgreSQL
- exposed through an API
- internal configuration only

---

## JobSummary

`JobSummary` is a result/artifact of an audit.

It does not necessarily need its own business module.

The generation logic belongs to AI.

The persistence relationship belongs to the audit/job domain.

---

## Upload

Upload is an operation, not necessarily a domain module.

A recommended conceptual model is:

```text
Audit
   |
   +--> Upload raw CSV
   |
   +--> Create Job
   |
   +--> Dispatch Processing
```

The developer must decide whether this warrants a dedicated module.

---

# 12. Recommended Core vs Business Boundary

A possible boundary is:

```text
app/
│
├── core/
│   ├── config/
│   ├── exceptions/
│   ├── logging/
│   ├── database/
│   ├── storage/
│   ├── queue/
│   ├── health/
│   ├── metrics/
│   └── security/
│
└── modules/
    ├── audits/
    ├── transactions/
    ├── processing/
    ├── anomalies/
    └── ai/
```

This is a recommended starting point, not a mandatory final architecture.

The developer should validate the structure against:

- `AGENTS.md`
- existing architecture documentation
- actual code
- module cohesion
- dependency direction

---

# 13. Implementation Order

The following is the recommended build sequence.

---

## Phase 0 — Repository and Architecture Review

Before coding:

1. Read `AGENTS.md`.
2. Confirm active application entry point.
3. Confirm current backend architecture.
4. Inspect current configuration implementation.
5. Inspect current exception implementation.
6. Inspect Docker and Compose.
7. Inspect CI.
8. Inspect tests.
9. Confirm Python/FastAPI/SQLAlchemy versions.

### Human decision checkpoint

Confirm the intended target architecture before continuing.

---

## Phase 1 — Complete Core Foundation

### 1. Configuration

Already complete.

### 2. Exception handling

Already complete.

### 3. Structured logging

Implement next.

### 4. Database infrastructure

Implement:

- SQLAlchemy async engine
- session factory
- base
- dependency integration

### 5. Alembic

Set up:

- migration environment
- initial migration strategy
- Docker integration

### 6. Dependency injection conventions

Document and establish:

- session injection
- service construction
- repository construction
- external dependency injection

### 7. Health/readiness

Implement health and readiness behavior.

### 8. Storage abstraction

Implement the S3-facing interface and adapter.

### 9. Queue abstraction

Establish Celery/Redis integration and task dispatching.

### 10. CORS

Implement before frontend integration.

---

# 14. Phase 2 — Database Domain Models

Create the models required by the PRD:

```text
Job
Transaction
JobSummary
AuditRule
BusinessApiKey (only if auth-lite is chosen)
```

Create relationships and constraints.

Generate Alembic migrations.

### Human decision checkpoint

Decide:

- which models are in v1
- database constraints
- indexing strategy
- enum implementation
- deletion cascade behavior
- transaction ownership

---

# 15. Phase 3 — First Vertical Slice

Build the smallest complete end-to-end workflow:

```text
POST /upload
     |
     v
Validate CSV
     |
     v
Create Job
     |
     v
Upload to S3
     |
     v
Dispatch Celery task
     |
     v
Worker receives job
     |
     v
Update Job status
```

At this point, do not implement all processing logic.

The goal is to prove:

```text
FastAPI
   |
PostgreSQL
   |
S3
   |
Celery
   |
Redis
```

all work together.

This should be the first major integration milestone.

---

# 16. Phase 4 — Audit and Transaction Modules

Implement:

1. Audit/job creation
2. Job status
3. Job listing
4. Transaction persistence
5. Result retrieval

Then verify the database lifecycle.

---

# 17. Phase 5 — Data Cleaning

Implement cleaning as part of the processing pipeline or as its own internal component based on the human architectural decision.

Requirements from the PRD:

- normalize dates
- normalize amounts
- uppercase status
- uppercase currency
- fill missing category
- drop exact duplicate rows
- record raw row count
- record clean row count

Test thoroughly with messy CSV inputs.

---

# 18. Phase 6 — Anomaly Detection

Implement in the specified priority order:

```text
1. Duplicate payment
2. Statistical outlier
3. Currency mismatch
```

Persist:

- `is_anomaly`
- `anomaly_reason`
- `duplicate_of_txn_id`

Add unit tests for each detector.

---

# 19. Phase 7 — AI / LLM Classification

Implement:

```text
Uncategorised transactions
        |
        v
Batch prompt
        |
        v
LLM
        |
        v
Validate JSON
        |
        v
Validate categories
        |
        v
Persist classification
```

Add:

- tenacity retries
- failure tracking
- raw response handling if chosen
- `llm_failed`

---

# 20. Phase 8 — AI Narrative Summary

Implement:

```text
Aggregated job statistics
        |
        v
LLM
        |
        v
Validated structured response
        |
        v
JobSummary
```

Generate:

- spend by currency
- top merchants
- anomaly count
- duplicate flagged amount
- narrative
- risk level

---

# 21. Phase 9 — Job Completion and Failure Handling

Implement:

```text
pending
   |
processing
   |
completed
```

and:

```text
processing
   |
failed
```

Ensure:

- `completed_at`
- `error_message`
- status transitions
- recoverable LLM failures
- retry endpoint

are handled consistently.

---

# 22. Phase 10 — Results and Export

Implement:

```text
GET /results
GET /export.csv
```

Results should provide:

- cleaned transactions
- flagged transactions
- anomaly grouping
- category breakdown
- narrative summary

Export should include:

- cleaned data
- anomaly fields
- category fields

---

# 23. Phase 11 — Delete and Retention

Implement:

```text
DELETE /v1/audits/{job_id}
```

Deletion should cover:

- Job
- Transactions
- JobSummary
- S3 object(s)

Then implement the retention strategy described by the PRD.

Potential components:

```text
S3 Lifecycle Policy
+
Job.expires_at
+
Database cleanup
```

### Human decision checkpoint

Decide:

- hard delete vs soft delete
- cleanup mechanism
- Celery Beat vs scheduled infrastructure
- exact retention semantics
- failure behavior if S3 and PostgreSQL deletion become inconsistent

---

# 24. Phase 12 — Metrics and Rate Limiting

Implement:

```text
/metrics
```

with required job and LLM metrics.

Implement rate limiting on `/upload`.

### Human decision checkpoint

Confirm:

- rate-limit key
- rate limit
- Redis implementation
- API-key strategy

---

# 25. Phase 13 — Frontend Integration

Implement the three PRD screens:

```text
1. Upload
2. Status polling
3. Results
```

Configure CORS.

Verify:

```text
React
  |
  v
FastAPI
  |
  v
Celery
  |
  v
Results
```

---

# 26. Phase 14 — Operational and Delivery Requirements

Complete:

- Docker Compose
- healthchecks
- automatic migrations
- CI
- README
- architecture diagram
- sample CSV
- curl examples
- environment documentation
- retention statement
- Kubernetes example manifests
- production architecture notes

---

# 27. Human Architectural Decision Register

The following decisions should be explicitly answered by the developer during implementation.

## A. Active backend architecture

- Is `backend/` definitively the active architecture?
- Is `api/` legacy?
- Should `api/` remain?
- Should `api/` eventually be removed?

## B. Application structure

- What exact module structure will be used?
- Will each business module contain router/service/repository/schema files?
- Where will shared models live?

## C. Database transaction ownership

- Service or repository?
- How are commits handled?
- How are rollbacks handled?

## D. Dependency injection

- How are services constructed?
- How are repositories constructed?
- How are infrastructure adapters injected?

## E. Exception architecture

- Exact hierarchy?
- Exact response schema?
- Which errors map to which codes?
- Which infrastructure errors are translated?

## F. Logging

- Logging library?
- JSON formatter?
- Request ID?
- Job ID?
- Trace/correlation ID?
- Redaction strategy?

## G. S3

- One bucket or multiple?
- Exact key convention?
- Upload through API or presigned URLs?
- Storage interface shape?

## H. Celery

- One queue or multiple?
- One task or multiple pipeline tasks?
- Retry ownership?
- Worker concurrency?
- Celery Beat?

## I. Processing pipeline

- One orchestrator or separate tasks?
- How are stage failures represented?
- Can processing resume from a failed stage?

## J. Data cleaning

- Dedicated module or processing subcomponent?
- pandas DataFrame lifecycle?
- Memory limits?

## K. Anomaly detection

- Separate detector classes?
- Multiple anomaly reasons per transaction or first-match only?
- Rule configuration strategy?

## L. LLM

- Client abstraction?
- Provider implementation?
- Prompt storage?
- Response validation?
- Batch size?
- Retry strategy?
- Raw response storage?

## M. Authentication

- No authentication?
- API keys?
- Full auth?

## N. Rate limiting

- IP?
- Business?
- API key?
- Exact limits?

## O. Retention

- S3 lifecycle only?
- Database cleanup?
- Scheduled Celery task?
- Soft delete or hard delete?

## P. Metrics

- Metric library?
- Metric naming?
- Labels?
- HTTP metrics?
- Worker metrics?

## Q. Frontend

- API base URL configuration?
- Polling interval?
- Error handling?
- CORS configuration?

---

# 28. Recommended Decision-Making Rule

For every architectural decision:

1. Check `AGENTS.md`.
2. Check existing repository conventions.
3. Check the PRD.
4. Identify the trade-offs.
5. Make an explicit human decision.
6. Document the decision if it affects architecture.

Do not let implementation convenience silently become architecture.

---

# 29. Definition of Done for the Foundation

Before considering the core foundation complete, verify:

- [ ] Configuration validation works.
- [ ] Centralized exception handling works.
- [ ] Structured logging works.
- [ ] `job_id` correlation is supported.
- [ ] Database sessions are correctly managed.
- [ ] SQLAlchemy async integration works.
- [ ] Alembic migrations work.
- [ ] Dependency injection conventions are established.
- [ ] S3 storage abstraction works.
- [ ] Celery/Redis infrastructure works.
- [ ] Health endpoint works.
- [ ] Readiness behavior is defined.
- [ ] CORS is configured appropriately.
- [ ] Metrics infrastructure is available.
- [ ] Rate limiting strategy is decided.
- [ ] Security/authentication decision is documented.

---

# 30. Definition of Done for Business Modules

## Audits

- [ ] Upload endpoint
- [ ] Job creation
- [ ] Job status
- [ ] Job listing
- [ ] Results
- [ ] Export
- [ ] Retry
- [ ] Delete

## Transactions

- [ ] Model
- [ ] Repository
- [ ] Persistence
- [ ] Retrieval
- [ ] Bulk operations
- [ ] Export support

## Processing

- [ ] Celery task
- [ ] Pipeline orchestration
- [ ] State transitions
- [ ] Failure handling
- [ ] Completion handling

## Anomalies

- [ ] Duplicate payment
- [ ] Statistical outlier
- [ ] Currency mismatch
- [ ] Priority behavior
- [ ] Tests

## AI

- [ ] Classification
- [ ] Batch processing
- [ ] JSON validation
- [ ] Retry
- [ ] Failure tracking
- [ ] Narrative summary
- [ ] Summary validation

---

# 31. Recommended Milestone Sequence

The project should ideally reach these milestones:

```text
Milestone 1
Core foundation
    |
    +--> Config
    +--> Exceptions
    +--> Logging
    +--> Database
    +--> Migrations
    +--> DI
    +--> Health

Milestone 2
Infrastructure
    |
    +--> S3
    +--> Celery
    +--> Redis
    +--> Queue dispatch

Milestone 3
First vertical slice
    |
    Upload
      ->
    Job
      ->
    S3
      ->
    Celery
      ->
    Worker
      ->
    Status

Milestone 4
Domain
    |
    +--> Audits
    +--> Transactions

Milestone 5
Processing
    |
    +--> Cleaning
    +--> Persistence

Milestone 6
Intelligence
    |
    +--> Anomalies
    +--> LLM Classification
    +--> LLM Summary

Milestone 7
Product API
    |
    +--> Results
    +--> Export
    +--> Retry
    +--> Delete
    +--> List

Milestone 8
Operational maturity
    |
    +--> Metrics
    +--> Rate limiting
    +--> Retention
    +--> Cleanup

Milestone 9
Frontend and delivery
    |
    +--> React
    +--> CORS
    +--> Docker
    +--> CI
    +--> Documentation
    +--> Kubernetes examples
```

---

# 32. Final Guiding Principle

The goal is not to build every possible abstraction before writing business logic.

The goal is to establish enough foundation that the business modules can be implemented cleanly without repeatedly solving the same infrastructure problems.

The intended dependency direction is:

```text
                    Business Modules
                          |
                          v
                 Application Interfaces
                          |
                          v
                 Core Infrastructure
                          |
                          v
          External Systems / Providers
```

For example:

```text
Audit Module
    |
    +--> Storage Interface ----> S3
    |
    +--> Queue Interface ------> Celery/Redis
    |
    +--> Repository -----------> PostgreSQL

AI Module
    |
    +--> LLM Interface --------> Gemini
```

This keeps business logic focused on LedgerGuard's actual purpose while keeping external technologies replaceable.

The most important implementation principle is:

> Build the foundation required to support the domain, but do not allow infrastructure concerns to become the domain itself.

At every architectural boundary, make the decision explicitly, document it when appropriate, and ensure the implementation remains consistent with `AGENTS.md`, the PRD, and the actual needs of the project.
