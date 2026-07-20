# AGENTS.md

This file is the single source of truth for backend architecture and development standards in this repository.

## Purpose

The backend must be built as a modular, scalable, production-oriented system with strong separation of concerns.
All future implementation work must follow these rules exactly.

## Architectural principles

### 1. Module-first backend architecture

The backend must be organized around business capabilities, not around database tables or generic layers alone.

Use this rule:
- core = shared infrastructure and cross-cutting concerns
- modules = business ownership and feature implementation

Do not build the backend as a flat API folder with feature logic scattered across it.

### 2. Strict separation of concerns

Each module must own its own vertical slice:
- controllers
- application layer
- domain layer
- infrastructure layer
- tests
- docs

A module should be able to evolve independently without leaking implementation details into other modules.

### 3. Domain-driven design boundaries

The backend must follow clear layer boundaries:
- controllers: thin request handlers only
- application: orchestration, use cases, commands, queries, DTO mapping
- domain: business rules, entities, value objects, repository contracts, domain services
- infrastructure: persistence implementations, external integrations, queue/workers, adapters

Business logic must not be mixed with HTTP, persistence, or external service code.

### 4. Validation is mandatory at every boundary

Never trust any input.
All external inputs must be validated before use.

Required validation rules:
- request DTOs validate incoming API payloads
- response DTOs shape outputs explicitly
- domain entities validate invariants
- repository/infrastructure layer validates data from external systems

Validation must be centralized and reusable where possible.
Do not duplicate validation logic across modules unless it is truly module-specific.

### 5. Domain logic must be independent of infrastructure

Business logic must not depend on:
- a specific ORM
- a specific database engine
- a specific queue implementation
- a specific external provider

The domain layer must depend on abstractions (interfaces/repository contracts), not concrete infrastructure implementations.

Infrastructure implementations are allowed to adapt data for the domain layer.

### 6. Cross-cutting concerns must be global and centralized

Cross-cutting concerns must live in core and be reused globally.
Examples:
- configuration and environment validation
- logging
- exception handling
- middleware
- security/authentication
- authorization guards
- dependency injection
- tracing
- pagination helpers
- shared utilities

These concerns must not be copied into every feature module.

### 7. Environment configuration must be validated early

All environment variables must be loaded through a strict configuration schema.
The application must fail fast if required configuration is missing or invalid.

Rules:
- define configuration in core/config
- validate values before app startup completes
- avoid ad-hoc environment access in business code

### 8. Tests are required for every module

Every module must include tests.

Required testing approach:
- unit tests for domain logic, validators, use cases, and business services
- integration tests for controllers, repositories, workers, and end-to-end flows
- tests should verify real behavior, not mock-only behavior

No feature should be considered complete without testing coverage for its core behavior.

## Required backend folder structure

The backend must follow this structure:

```text
backend/
  app/
    main.py

    core/
      config/
      dependencies/
      exceptions/
      middleware/
      logging/
      security/
      utils/

    modules/
      <module>/
        controllers/
        application/
          dto/
            request/
            response/
          commands/
          queries/
          services/
          mappers/
        domain/
          entities/
          value_objects/
          repositories/
          services/
        infrastructure/
          persistence/
          external/
          mappers/
        docs/
        tests/
```

## Module contract

Every business capability must be implemented as a module.

Each module must contain:

### controllers/
Thin HTTP entry points only.
Controllers must:
- receive request input
- validate request DTOs
- call application services
- return structured responses

Controllers must not contain business logic.

### application/dto/request/
Request DTOs for incoming data.
These define validation rules and transport contract.

### application/dto/response/
Response DTOs for outgoing data.
These define the API response shape.

### application/commands/
Write-oriented use cases.
Use this for operations such as create, update, approve, start, complete, etc.

### application/queries/
Read-oriented use cases.
Use this for fetching data or building summaries.

### application/services/
Application orchestration services.
This layer coordinates use cases and delegates to domain services and infrastructure implementations.

### application/mappers/
Mapping from domain/application objects to API-facing response objects.

### domain/entities/
Core business entities.
These are not persistence models and should not be tied to ORM classes.

### domain/value_objects/
Small business concepts with strong meaning, such as money, dates, status values, identifiers, or ranges.

### domain/repositories/
Repository contracts only.
These are abstractions. They must not contain ORM-specific code.

### domain/services/
Pure business logic that expresses domain rules.
This layer should be framework-light.

### infrastructure/persistence/
Concrete persistence implementations.
Examples: ORM repositories, database adapters, query composition, repository implementations.

### infrastructure/external/
Third-party integrations.
Examples: payment providers, email providers, storage providers, notification services, AI integrations.

### infrastructure/mappers/
Mapping between persistence/external provider shapes and domain/application types.

### docs/
Swagger notes, response docs, reusable docs decorators, examples.

### tests/
Module-local tests for the feature.

## Core layer rules

The core layer is shared infrastructure and should contain reusable things only.

It must include:
- configuration and settings validation
- dependency injection helpers
- exception handling infrastructure
- logging infrastructure
- security/auth infrastructure
- routing/middleware infrastructure
- shared utilities

Core code must not contain feature-specific business rules.

## API rules

Every API endpoint must follow these rules:
- use module-local controllers
- use module-local request and response DTOs
- validate incoming data through DTOs and validators
- keep controllers thin
- delegate business work to application services
- return structured response DTOs

## Dependency rules

Dependency direction must always be inward:
- controllers depend on application services
- application services depend on domain services and repository interfaces
- domain services depend on domain abstractions only
- infrastructure implementations depend on domain contracts and external adapters

The dependency direction must never go from infrastructure to application or domain in a way that bypasses the abstraction boundary.

## Naming conventions

Use clear, explicit names:
- modules: lowercase snake_case folder names
- files: lowercase snake_case
- classes: PascalCase
- functions and methods: snake_case

## Implementation expectations

When implementing new backend features:
1. Create or update the module structure under backend/app/modules/<module>/
2. Put request DTOs in application/dto/request
3. Put response DTOs in application/dto/response
4. Implement controller in controllers/
5. Add application services or commands/queries as needed
6. Add domain logic in domain/
7. Implement persistence or external integrations in infrastructure/
8. Add tests in tests/
9. Keep shared concerns in core/

## Non-negotiable requirements

The following rules are mandatory and must be followed in all development work:
- module-first architecture
- no business logic in controllers
- no infrastructure logic in domain layer
- validation for all incoming and outgoing data
- repository abstractions in domain layer
- concrete implementations in infrastructure layer
- core shared concerns centralized and reusable
- environment variables validated before runtime
- unit and integration tests for modules
- no feature should be implemented in a way that violates these boundaries
