import time

from app.core.infrastructure.celery_app import celery_app
from app.core.logging import get_logger, log_stage, set_correlation_context

logger = get_logger(__name__)


@celery_app.task(name="app.core.infrastructure.tasks.ping")
def ping(job_id: str | None = None) -> str:
    """Dummy task: sleeps 1s then returns 'pong'."""
    with set_correlation_context(job_id=job_id, service="celery", component="tasks"):
        logger.info("celery task started", extra={"event": "task_started"})
        with log_stage(logger, "ping", event="task_completed"):
            time.sleep(1)
        logger.info("celery task completed", extra={"event": "task_completed", "result": "pong"})
        return "pong"
