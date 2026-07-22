# Structured Logging and Correlation

## Purpose

LedgerGuard uses structured JSON logging so that operations can be traced across the FastAPI request lifecycle, Redis/Celery background processing, and downstream task execution. The logging design is centered on the asynchronous business identifier `job_id`, which allows every log emitted for a single audit workflow to be correlated quickly.

## Architecture

The logging system is implemented in the shared backend core package so that both the HTTP entrypoint and the worker runtime use the same formatting and correlation behavior.

```text
FastAPI
  |
  v
Redis / Celery boundary
  |
  v
Celery worker
  |
  v
Processing pipeline
```

## Logging stack

- Library: Python `logging` with a custom JSON formatter
-Handler: `StreamHandler` writing to standard output
- Output destination: stdout/stderr so container platforms can collect logs
- Correlation: `contextvars`-based context scoped to each request or task

## Log schema

Every log entry is emitted as a single JSON object with the following standard fields:

- `timestamp`: UTC ISO-8601 timestamp
- `level`: log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `message`: human-readable message
- `event`: event name such as `request_received` or `job_created`
- `job_id`: correlation identifier for the audit workflow when available
- `request_id`: correlation identifier for the HTTP request when available
- `stage`: current processing stage when relevant
- `service`: logical service name (`api`, `celery`)
- `component`: component name such as `fastapi` or `tasks`
- `exception_type`: exception class name when an exception is logged
- `exception_message`: safe exception text for internal debugging
- `duration_ms`: elapsed time for stage-level operations

Sensitive fields such as `api_key`, `authorization`, `password`, `token`, and `access_token` are redacted automatically.

## Correlation strategy

The primary correlation field is `job_id`. Request-scoped correlation is also supported through `request_id` when the request boundary provides one. The implementation does not treat them as interchangeable: `request_id` identifies a single HTTP request, while `job_id` identifies the broader asynchronous workflow.

## Context propagation

Correlation state is stored in a `ContextVar` and is scoped to a specific execution context. FastAPI request handling and Celery task execution each establish their own context before emitting logs, and that context is reset after the request or task completes. This prevents logs from one request or task from leaking into another.

## Celery integration

The Celery task entrypoint receives `job_id` explicitly from the FastAPI request path and establishes worker-side correlation context before starting execution. The task then logs structured events for stage execution and completion.

## Exception handling integration

The shared exception handlers continue to shape client-facing error responses, while the logging layer captures structured diagnostic context for internal debugging. Unexpected exceptions are logged as structured events without exposing unexpected internal detail to clients.

## Log levels

- `DEBUG`: low-level diagnostics
- `INFO`: lifecycle and stage events such as request receipt, task start, stage start, stage completion, and task completion
- `WARNING`: recoverable issues and handled exceptions
- `ERROR`: operational failures that require investigation
- `CRITICAL`: severe failures that may impact service availability

## Event naming

Events follow a simple convention:

- `<domain>_started`
- `<domain>_completed`
- `<domain>_failed`
- `<component>_exception_handled`

## Stage logging

Stage-level logging is available through the shared helper used by background processing. Each stage logs a start event, then a completion event with `duration_ms` when it finishes successfully.

## Local development

Run the application with Docker Compose as usual and inspect logs with:

```bash
docker compose logs -f backend
```

## Testing

The logging behavior is covered by unit tests that verify JSON output, required fields, correlation context, stage timing, and redaction.

## Troubleshooting

- To find all logs for a workflow, search for the `job_id` value in your log aggregation system.
- To identify the failed stage, inspect the `stage` field and the related `event` value.
- To distinguish request-level and workflow-level correlation, compare `request_id` and `job_id` in the same log entry.

## Architectural decisions

The implementation uses Python's built-in `logging` module plus a custom JSON formatter. A separate OpenTelemetry or external logging platform was not introduced because the repository did not define one.
