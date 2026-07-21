# Exception handling core

This document is the single source of truth for the centralized exception handling system used by the backend.

## Purpose

Centralized exception handling ensures that application code can raise typed business errors without scattering repetitive try/except blocks through routers or controllers. The backend uses a shared exception core so that:

- expected application errors become consistent HTTP responses
- unexpected failures are handled safely and logged internally
- sensitive implementation details are never leaked to API clients
- services and domain logic can raise domain-level exceptions without depending on FastAPI directly

## Core concepts

### 1. Expected application exceptions

These are the normal, intentional errors that represent business or validation outcomes such as:

- not found resources
- conflicts
- bad requests
- forbidden access
- unauthorized access
- temporary upstream failures

These exceptions are raised from application, service, or domain layers using the shared exception classes defined in the core package.

### 2. Infrastructure exceptions

Low-level failures from infrastructure boundaries such as external services, databases, or cache layers should be translated at the boundary where they are handled. They should not be exposed directly to clients.

The preferred pattern is:

1. catch the infrastructure exception at the adapter or repository boundary
2. translate it into a typed application exception
3. re-raise it so the global handler can produce a consistent API response

### 3. Unexpected exceptions

Unexpected failures are any exceptions that were not explicitly anticipated by the application logic. These should be handled centrally, logged with a full traceback internally, and returned to clients as a safe generic 500 response.

## How the system works

The exception flow is:

1. A route, controller, service, or domain layer raises an exception.
2. The exception bubbles upward through the request stack.
3. FastAPI and Starlette middleware route the exception through the registered handlers.
4. The handler maps the exception to a consistent JSON response.
5. The client receives a safe, structured error payload.

The implementation avoids duplicate route-level boilerplate and keeps the HTTP response behavior centralized.

## Project implementation

The exception core lives under:

- [backend/app/core/exceptions](../backend/app/core/exceptions)

The main integration point is:

- [backend/app/main.py](../backend/app/main.py)

The backend app factory registers the exception handlers during app creation, so the behavior applies to the actual running application and to tests that use the same app instance.

## Files in the exception core

### [backend/app/core/exceptions/base.py](../backend/app/core/exceptions/base.py)

Defines the base exception model used across the project.

Responsibilities:

- defines AppException as the common base class for expected application errors
- stores transport metadata such as status code and error code
- carries a safe human-readable message
- supports optional structured details
- exposes a method that converts the exception into a standardized error response payload

### [backend/app/core/exceptions/common.py](../backend/app/core/exceptions/common.py)

Defines the initial exception hierarchy used by the backend.

Included exception types:

- BadRequestError
- UnauthorizedError
- ForbiddenError
- NotFoundError
- ConflictError
- TooManyRequestsError
- ServiceUnavailableError
- InternalServerError

Each one provides a stable error code and an appropriate HTTP status.

### [backend/app/core/exceptions/handlers.py](../backend/app/core/exceptions/handlers.py)

Contains the global FastAPI exception handlers and the request middleware fallback.

Responsibilities:

- maps AppException instances to consistent JSON responses
- normalizes request validation errors into a structured validation payload
- normalizes FastAPI/Starlette HTTP exceptions into the project error contract
- logs unexpected exceptions with traceback information
- returns a safe generic 500 response for unhandled errors

### [backend/app/core/exceptions/schemas.py](../backend/app/core/exceptions/schemas.py)

Defines the data structures used for error payloads and validation details.

This keeps the response model explicit and makes it easier to evolve the API contract over time.

### [backend/app/core/exceptions/__init__.py](../backend/app/core/exceptions/__init__.py)

Exports the exception core publicly so other modules can import from a single location.

### [backend/app/core/exceptions/README.md](../backend/app/core/exceptions/README.md)

Provides implementation notes and usage guidance for developers working on the backend.

## Error response contract

The API uses a consistent envelope:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found.",
    "details": null
  }
}
```

Validation errors use the same shape but include structured field details:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": {
      "fields": [
        {
          "loc": ["body", "quantity"],
          "msg": "Input should be a valid integer",
          "type": "int_parsing"
        }
      ]
    }
  }
}
```

## Preferred usage pattern

Application and service code should raise typed exceptions like this:

```python
from app.core.exceptions import NotFoundError

if resource is None:
    raise NotFoundError("resource")
```

Routes and controllers should remain thin and should not add repetitive try/except blocks purely to return HTTP responses.

## Guidance for future development

When adding new module-specific behavior:

1. use the shared exception base if the error is an application-level concern
2. create a specific exception class only when the error needs a unique meaning or code
3. raise it from the appropriate service or domain boundary
4. let the global handlers convert it into the standard API response
5. avoid leaking tracebacks, secrets, or infrastructure details to clients

## Celery and background tasks

The exception system is designed for FastAPI HTTP handling. Celery workers use their own execution model and should continue to handle task-level failures through their own task and retry logic. The shared exception classes can still be used by background task code when the business error needs to be represented consistently, but the HTTP and worker execution paths remain separate.
