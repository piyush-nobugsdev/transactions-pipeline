import asyncio
import time
from datetime import datetime, timezone
from uuid import UUID

from app.core.database.session import AsyncSessionLocal
from app.core.infrastructure.celery_app import celery_app
from app.core.logging import get_logger, log_stage, set_correlation_context
from app.modules.audits.infrastructure.persistence.sqlalchemy_job_repository import SqlAlchemyJobRepository
from app.schemas.models import JobStatus

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


@celery_app.task(name="app.core.infrastructure.tasks.process_audit_job")
def process_audit_job(job_id: str) -> str:
    """Minimal processing pipeline stub: mark processing, wait briefly, then complete the job."""
    job_uuid = UUID(job_id)

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            repository = SqlAlchemyJobRepository(session)
            await repository.update(job_uuid, status=JobStatus.PROCESSING)
            await session.commit()
            await asyncio.sleep(0.1)
            await repository.update(
                job_uuid,
                status=JobStatus.COMPLETED,
                row_count_raw=0,
                row_count_clean=0,
                completed_at=datetime.now(timezone.utc),
                error_message=None,
            )
            await session.commit()

    with set_correlation_context(job_id=job_id, service="celery", component="audit-processing"):
        logger.info("audit processing started", extra={"event": "processing_started"})
        asyncio.run(_run())
        logger.info("audit processing completed", extra={"event": "processing_completed"})
        return job_id
