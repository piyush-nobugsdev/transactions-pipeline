# Centralized exception handling

The backend uses a shared exception core under app/core/exceptions so that application code can raise typed business exceptions without repeating route-level try/except blocks.

## Exception flow

1. Application and service code raise a project exception such as NotFoundError or ConflictError.
2. FastAPI routes remain thin and simply propagate the exception.
3. The global handlers in app/core/exceptions/handlers.py convert the exception into a consistent JSON payload.
4. Unexpected exceptions are logged with a full traceback and converted into a safe 500 response.

## Preferred usage

- Raise application exceptions from services, commands, and domain logic.
- Keep controllers focused on request/response handling.
- Avoid adding try/except around every route just to map errors to HTTP responses.
- Translate infrastructure failures at the boundary where the low-level exception is first handled.

## Example

```python
from app.core.exceptions import NotFoundError

class UserService:
    async def get_user(self, user_id: str) -> dict[str, object]:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("user")
        return user.to_dict()
```

## Notes

- Client-facing responses never expose raw tracebacks or implementation details.
- Validation errors are normalized into a structured payload with field-level details.
- Celery workers use the same exception classes for business logic, but their own error handling remains separate from FastAPI HTTP handlers.
