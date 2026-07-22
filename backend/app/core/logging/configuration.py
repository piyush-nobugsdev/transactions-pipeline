from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Mapping, TextIO

from app.core.config import get_settings
from app.core.logging.context import build_log_context


class JsonFormatter(logging.Formatter):
    _reserved_fields = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        extra_fields = getattr(record, "extra_fields", {})
        if isinstance(extra_fields, Mapping):
            payload.update(extra_fields)

        for key, value in record.__dict__.items():
            if key in self._reserved_fields or key.startswith("_"):
                continue
            payload[key] = value

        correlation_fields = build_log_context()
        if correlation_fields:
            payload.update(correlation_fields)

        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            payload["exception_type"] = exc_type.__name__ if exc_type else None
            payload["exception_message"] = str(exc_value) if exc_value else None

        if record.name:
            payload["logger_name"] = record.name

        if not payload.get("event"):
            payload["event"] = record.getMessage()

        return json.dumps(self._sanitize_payload(payload), sort_keys=True)

    def _sanitize_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in payload.items():
            if key in {"authorization", "api_key", "password", "token", "access_token", "secret"}:
                sanitized[key] = "<redacted>"
            elif isinstance(value, str) and value.startswith("Bearer "):
                sanitized[key] = "<redacted>"
            elif isinstance(value, (dict, list)):
                sanitized[key] = self._sanitize_payload(value) if isinstance(value, dict) else [self._sanitize_payload(v) if isinstance(v, dict) else v for v in value]
            else:
                sanitized[key] = value
        return sanitized


def configure_logging(*, stream: TextIO | None = None, level: str | None = None, force: bool = False) -> None:
    if stream is None:
        stream = sys.stdout

    try:
        settings = get_settings()
    except Exception:
        settings = None

    configured_level = level or os.getenv("LOG_LEVEL")
    if not configured_level and settings is not None and getattr(settings, "LOG_LEVEL", None):
        configured_level = str(settings.LOG_LEVEL)
    log_level = str(configured_level or "INFO").upper()

    root_logger = logging.getLogger()
    if force:
        for existing_handler in list(root_logger.handlers):
            root_logger.removeHandler(existing_handler)
            existing_handler.close()

    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.propagate = False

    if not root_logger.handlers:
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        root_logger.addHandler(handler)

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("redis").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name or __name__)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
        extra = kwargs.get("extra") or {}
        if not isinstance(extra, dict):
            extra = {}
        extra_fields = dict(extra)
        extra_fields.setdefault("event", msg)
        kwargs["extra"] = {"extra_fields": extra_fields}
        return msg, kwargs


def get_structured_logger(name: str | None = None) -> StructuredLoggerAdapter:
    return StructuredLoggerAdapter(get_logger(name), {})
