from __future__ import annotations

import contextvars
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator, Mapping


@dataclass(slots=True)
class CorrelationContext:
    job_id: str | None = None
    request_id: str | None = None
    stage: str | None = None
    service: str | None = None
    component: str | None = None


_current_context: contextvars.ContextVar[CorrelationContext | None] = contextvars.ContextVar(
    "ledgerguard_correlation_context",
    default=None,
)


def get_correlation_context() -> CorrelationContext:
    context = _current_context.get()
    if context is None:
        return CorrelationContext()
    return context


@contextmanager
def set_correlation_context(
    *,
    job_id: str | None = None,
    request_id: str | None = None,
    stage: str | None = None,
    service: str | None = None,
    component: str | None = None,
) -> Iterator[None]:
    previous = _current_context.get()
    new_context = CorrelationContext(
        job_id=job_id if job_id is not None else previous.job_id if previous is not None else None,
        request_id=request_id if request_id is not None else previous.request_id if previous is not None else None,
        stage=stage if stage is not None else previous.stage if previous is not None else None,
        service=service if service is not None else previous.service if previous is not None else None,
        component=component if component is not None else previous.component if previous is not None else None,
    )
    token = _current_context.set(new_context)
    try:
        yield
    finally:
        _current_context.reset(token)


def clear_correlation_context() -> None:
    _current_context.set(None)


def build_log_context(extra: Mapping[str, object] | None = None) -> dict[str, object]:
    context = get_correlation_context()
    payload = {}
    if context.job_id is not None:
        payload["job_id"] = context.job_id
    if context.request_id is not None:
        payload["request_id"] = context.request_id
    if context.stage is not None:
        payload["stage"] = context.stage
    if context.service is not None:
        payload["service"] = context.service
    if context.component is not None:
        payload["component"] = context.component
    if extra:
        payload.update(extra)
    return payload


@contextmanager
def log_stage(logger, stage: str, *, event: str = "processing_stage_completed") -> Iterator[None]:
    started_at = time.perf_counter()
    logger.info("processing stage started", extra={"event": f"{stage}_started", "stage": stage})
    try:
        yield
    except Exception as exc:
        logger.exception(
            "processing stage failed",
            extra={
                "event": f"{stage}_failed",
                "stage": stage,
                "exception_type": type(exc).__name__,
            },
        )
        raise
    else:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "processing stage completed",
            extra={
                "event": event,
                "stage": stage,
                "duration_ms": elapsed_ms,
            },
        )
