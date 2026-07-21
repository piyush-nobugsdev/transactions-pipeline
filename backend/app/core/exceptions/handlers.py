from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .base import AppException, ErrorDetails, ErrorResponse, ErrorResponseModel
from .common import InternalServerError

logger = logging.getLogger(__name__)


def _build_error_payload(code: str, message: str, details: ErrorDetails | None = None) -> ErrorResponse:
    return ErrorResponse(error=ErrorResponseModel(code=code, message=message, details=details))


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    payload = exc.to_response()
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = {"fields": []}
    for error in exc.errors():
        details["fields"].append(
            {
                "loc": error.get("loc", []),
                "msg": error.get("msg", "Invalid value"),
                "type": error.get("type", "validation_error"),
            }
        )
    payload = _build_error_payload("VALIDATION_ERROR", "Request validation failed.", details)
    return JSONResponse(status_code=422, content=payload.model_dump())


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    payload = _build_error_payload("HTTP_ERROR", exc.detail if isinstance(exc.detail, str) else "Request failed.", None)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        extra={
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
        },
    )
    fallback = InternalServerError()
    payload = fallback.to_response()
    return JSONResponse(status_code=fallback.status_code, content=payload.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    @app.middleware("http")
    async def exception_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except AppException as exc:
            return await app_exception_handler(request, exc)
        except RequestValidationError as exc:
            return await request_validation_exception_handler(request, exc)
        except StarletteHTTPException as exc:
            return await http_exception_handler(request, exc)
        except Exception as exc:
            return await generic_exception_handler(request, exc)
