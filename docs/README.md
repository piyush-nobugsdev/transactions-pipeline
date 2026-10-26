# Project Documentation

This folder is the canonical home for project documentation. Keep implementation
status and technical contracts here; component-local documentation should link
back to the relevant page in this folder rather than repeat its content.

The repository-level [README](../README.md) is a quickstart and entry point.
Backend coding and architecture rules remain in [AGENTS.md](../AGENTS.md).

## Product and roadmap

- [Product requirements](product-requirements.md) — intended product behavior and
  non-functional requirements. Requirements are not claims that a feature is
  already implemented.
- [Project plan](project-plan.md) — milestones, current progress, and remaining
  work. Use the module documents below for authoritative implementation details.

## Architecture and operations

- [Backend architecture](backend-architecture.md) — current module-first structure
  and dependency boundaries.
- [Configuration](config.md) — environment settings and validation.
- [Database and migrations](database-and-migration.md) — persistence and schema
  evolution.
- [Exception handling](exceptions.md) — shared error contract.
- [Structured logging](structured-logging-and-correlation.md) — log format and
  correlation.
- [CI/CD and local verification](ci_cd.md) — current automation, commands, and
  operational checks.
- [Frontend](frontend.md) — the current web client stack, upload flow, and gaps.

## Business modules

- [Audits and jobs](audits-jobs-module.md)
- [Transactions](transactions-module.md)
- [Processing](processing-module.md)
- [Anomaly detection](anomalies-module.md)

Update the relevant module document when behavior or API contracts change, then
update the roadmap if project progress or milestone ordering changes.
