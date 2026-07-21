from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, Field


class ErrorDetails(dict[str, Any]):
    """Mutable error details container with safe typing."""


class ErrorResponseModel(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Safe human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Optional structured details")


class ErrorResponse(BaseModel):
    error: ErrorResponseModel


class AppException(Exception):
    """Base exception for expected application errors."""

    status_code: int = 500
    code: str = "INTERNAL_SERVER_ERROR"
    message: str = "An unexpected error occurred."
    details: ErrorDetails | None = None

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        safe_message = message if message is not None else self.message
        super().__init__(safe_message)
        self.message = safe_message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        if details is not None:
            self.details = ErrorDetails(dict(details))
        else:
            self.details = None

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(error=ErrorResponseModel(code=self.code, message=self.message, details=self.details))

    def __str__(self) -> str:
        return self.message
