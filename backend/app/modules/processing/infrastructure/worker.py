from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.database.session import AsyncSessionLocal
from app.core.infrastructure.celery_app import celery_app
from app.core.logging import get_logger, set_correlation_context
from app.core.storage.dependencies import get_storage
from app.modules.audits.infrastructure.persistence.sqlalchemy_job_repository import SqlAlchemyJobRepository
from app.modules.processing.application.services.processing_service import ProcessingService
from app.modules.transactions.infrastructure.persistence.sqlalchemy_transaction_repository import (
    SqlAlchemyTransactionRepository,
)

logger = get_logger(__name__)


@celery_app.task(name="app.core.infrastructure.tasks.process_audit_job")
def process_audit_job(job_id: str) -> str:
    job_uuid = UUID(job_id)

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            service = ProcessingService(
                job_repository=SqlAlchemyJobRepository(session),
                transaction_repository=SqlAlchemyTransactionRepository(session),
                storage=get_storage(),
                unit_of_work=session,
            )
            await service.process(job_uuid)

    with set_correlation_context(job_id=job_id, service="celery", component="audit-processing"):
        logger.info("audit processing started", extra={"event": "processing_started"})
        asyncio.run(_run())
        logger.info("audit processing completed", extra={"event": "processing_completed"})
        return job_id
