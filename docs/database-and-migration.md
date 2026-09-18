# Database and Migration

This document is the single source of truth for the database and migration layer in this project.

## Purpose

The database layer provides persistent storage for the application domain, while migrations provide a safe and versioned way to evolve the schema over time. In this repository, the database foundation is designed to be:

- asynchronous
- configuration-driven
- schema-versioned
- reusable across the backend application

## Core concepts

### Database
A database stores the application’s structured data so it can be queried, updated, and retained beyond a single process run. In this project, the primary database is PostgreSQL.

### Migration
A migration is a versioned change to the database schema. It describes how to move the schema from one state to another, for example:

- creating a table
- adding a column
- adding an index
- changing a type
- removing a constraint

Migrations are important because they let the team evolve the schema safely and consistently across environments.

## Technologies used

The backend uses the following stack for persistence and schema evolution:

- PostgreSQL as the relational database engine
- SQLAlchemy 2.x for ORM models and async database access
- Alembic for schema migrations
- asyncpg as the PostgreSQL async driver
- Pydantic settings for environment-based configuration
- Docker Compose for local database services

## How the database layer works

### 1. Configuration
The application reads database settings from environment variables through the settings object in [backend/app/core/config/__init__.py](../backend/app/core/config/__init__.py). This includes:

- database user and password
- database name
- database URL

The settings object validates the required environment values before the app uses them.

### 2. Async engine and session factory
The database session layer is created in [backend/app/core/database/session.py](../backend/app/core/database/session.py). It:

- creates an async SQLAlchemy engine
- configures a session factory for async database operations
- enables connection pool pre-ping for reliability

This allows the application to use async database access rather than blocking synchronous I/O.

### 3. Declarative base
The shared SQLAlchemy base class is defined in [backend/app/core/database/base.py](../backend/app/core/database/base.py). All ORM models inherit from this base so they share a common metadata registry.

### 4. Dependency injection for request handling
The database dependency in [backend/app/core/database/dependencies.py](../backend/app/core/database/dependencies.py) provides a reusable async database session for the backend application. This makes it easy for service or route code to obtain a database session consistently.

### 5. Schema definition with ORM models
The concrete database models are declared in [backend/app/schemas/models.py](../backend/app/schemas/models.py). These models define the tables, columns, enums, indexes, defaults, and relationships that make up the persistence layer.

### 6. Migration execution
Alembic reads the current schema state, compares it to the migration scripts, and applies or rolls back changes as needed. The migration environment is configured in [backend/migrations/env.py](../backend/migrations/env.py), and the migration configuration lives in [backend/alembic.ini](../backend/alembic.ini).

## How it is implemented in this project

The current project uses a modular backend structure where persistence concerns are kept in the core database package and domain schema definitions are centralized in the schema models module.

### Current persistence model
The initial schema includes these entities:

- jobs
- job_summaries
- transactions

These tables support the workflow of ingesting files, processing transactions, and storing job-level summaries and anomaly information.

## Files in the database and migration layer

### [backend/app/core/database/base.py](../backend/app/core/database/base.py)
Defines the shared SQLAlchemy declarative base.

Responsibilities:
- provides the common base class for all ORM models
- registers model metadata in one place
- keeps the persistence layer consistent across modules

### [backend/app/core/database/session.py](../backend/app/core/database/session.py)
Creates the async SQLAlchemy engine and session factory.

Responsibilities:
- builds the async database engine
- configures the sessionmaker for async sessions
- centralizes connection setup for the application

### [backend/app/core/database/dependencies.py](../backend/app/core/database/dependencies.py)
Provides the dependency function used to obtain a database session.

Responsibilities:
- exposes a reusable dependency for database access
- manages the lifecycle of a session for request-bound operations
- keeps database access out of business logic and route handlers

### [backend/app/core/config/__init__.py](../backend/app/core/config/__init__.py)
Loads and validates environment settings for the database and related services.

Responsibilities:
- defines the application settings object
- enforces required database environment variables
- provides shared configuration to the database layer

### [backend/app/schemas/models.py](../backend/app/schemas/models.py)
Defines the SQLAlchemy ORM models for the application.

Responsibilities:
- declares tables and columns
- defines enums, indexes, defaults, and constraints
- represents the current schema in Python code

### [backend/alembic.ini](../backend/alembic.ini)
Contains the Alembic configuration for migration discovery and execution.

Responsibilities:
- points Alembic to the migration scripts folder
- defines the migration template location
- provides the base configuration for migration commands

### [backend/migrations/env.py](../backend/migrations/env.py)
Configures Alembic’s runtime environment for both offline and online migrations.

Responsibilities:
- loads the configured database URL from settings
- wires Alembic to the SQLAlchemy metadata
- runs migrations against the current database connection

### [backend/migrations/versions/8bd2ac0d369b_initial_schema.py](../backend/migrations/versions/8bd2ac0d369b_initial_schema.py)
The initial migration that creates the first version of the schema.

Responsibilities:
- creates the jobs table
- creates the job_summaries table
- creates the transactions table
- adds indexes and constraints needed by the initial design

### [docker-compose.yml](../docker-compose.yml)
Defines the local PostgreSQL service used for development and testing.

Responsibilities:
- starts a PostgreSQL container
- exposes the database port locally
- provides environment values used by the backend application

## Typical migration workflow

A standard workflow in this project looks like this:

1. update or add ORM models in [backend/app/schemas/models.py](../backend/app/schemas/models.py)
2. create a new Alembic revision
3. review the generated migration script
4. apply the migration to the target environment

A typical command sequence is:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Design notes

The current database design follows a few important principles:

- persistence is centralized and reusable
- schema evolution is versioned and explicit
- the database access layer is async and environment-driven
- application code should depend on shared database abstractions rather than ad-hoc connection handling

## Summary

The database and migration system in this repository is the foundation for storing and evolving application data safely. It combines PostgreSQL, SQLAlchemy, Alembic, and configuration-driven setup to provide a reliable persistence layer for the backend.
