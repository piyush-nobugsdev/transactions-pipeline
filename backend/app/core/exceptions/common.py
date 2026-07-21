from __future__ import annotations

from typing import Any, Mapping

from .base import AppException


class BadRequestError(AppException):
    status_code = 400
    code = "BAD_REQUEST"
    message = "The request is invalid."


class UnauthorizedError(AppException):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "Authentication is required."


class ForbiddenError(AppException):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class NotFoundError(AppException):
    status_code = 404
    code = "RESOURCE_NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppException):
    status_code = 409
    code = "RESOURCE_CONFLICT"
    message = "The resource already exists."


class TooManyRequestsError(AppException):
    status_code = 429
    code = "TOO_MANY_REQUESTS"
    message = "Too many requests."


class ServiceUnavailableError(AppException):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "The service is temporarily unavailable."


class InternalServerError(AppException):
    status_code = 500
    code = "INTERNAL_SERVER_ERROR"
    message = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message or self.message, status_code=self.status_code, code=self.code, details=details)
