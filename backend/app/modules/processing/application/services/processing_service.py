from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.storage.interface import Storage
from app.modules.audits.domain.entities import JobStatus
from app.modules.audits.domain.repositories.job_repository import JobRepository
from app.modules.transactions.domain.repositories.transaction_repository import TransactionRepository

from ...domain.services.csv_cleaner import clean_transactions

logger = get_logger(__name__)


class UnitOfWork(Protocol):
    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    job_id: UUID
    row_count_raw: int
    row_count_clean: int


class ProcessingService:
    def __init__(
        self,
        *,
        job_repository: JobRepository,
        transaction_repository: TransactionRepository,
        storage: Storage,
        unit_of_work: UnitOfWork,
    ) -> None:
        self.job_repository = job_repository
        self.transaction_repository = transaction_repository
        self.storage = storage
        self.unit_of_work = unit_of_work

    async def process(self, job_id: UUID) -> ProcessingResult:
        job = await self.job_repository.get(job_id)
        if job is None:
            raise NotFoundError("job")

        await self.job_repository.update(
            job_id,
            status=JobStatus.PROCESSING,
            completed_at=None,
            error_message=None,
        )
        await self.unit_of_work.commit()

        try:
            content = await self.storage.download(key=job.s3_key)
            row_count_raw, records = clean_transactions(content, job_id=job.id)
            await self.transaction_repository.bulk_create(records)
            await self.job_repository.update(
                job_id,
                status=JobStatus.COMPLETED,
                row_count_raw=row_count_raw,
                row_count_clean=len(records),
                completed_at=datetime.now(UTC),
                error_message=None,
            )
            await self.unit_of_work.commit()
            return ProcessingResult(job.id, row_count_raw, len(records))
        except Exception as exc:
            await self.unit_of_work.rollback()
            error_message = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Audit processing failed due to an internal error."
            )
            await self.job_repository.update(
                job_id,
                status=JobStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message=error_message[:2000],
            )
            await self.unit_of_work.commit()
            logger.exception(
                "audit processing failed",
                extra={"event": "processing_failed", "job_id": str(job_id)},
            )
            raise
