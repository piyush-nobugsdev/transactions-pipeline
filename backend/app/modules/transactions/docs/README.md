# Transactions Module

This module owns normalized transaction persistence and retrieval for an audit job.

## Responsibilities

- persist transaction rows created from a job's processed CSV
- retrieve transactions by ID or by job
- support bulk insert for cleaning and processing stages
- keep HTTP and persistence concerns outside the domain model

## Endpoints

- `POST /v1/transactions`
- `GET /v1/transactions?job_id=<uuid>&offset=0&limit=50`
- `GET /v1/transactions/{transaction_id}`
- `DELETE /v1/transactions/{transaction_id}`

## Boundaries

- controller: request validation and response shaping only
- application service: orchestration and use-case logic
- domain: transaction entity and repository contract
- infrastructure: SQLAlchemy repository adapter
