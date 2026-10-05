from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.core.infrastructure.celery_app import celery_app
from app.core.logging import get_logger
from app.core.storage.interface import Storage

from ...domain.entities import JobRecord, JobStatus
from ...domain.repositories.job_repository import JobRepository
from ..dto.request.job_requests import CreateJobRequest

logger = get_logger(__name__)


class JobService:
    def __init__(
        self,
        repository: JobRepository,
        storage: Storage | None = None,
        *,
        storage_bucket: str = "configured-storage",
        retention_days: int = 30,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.storage_bucket = storage_bucket
        self.retention_days = retention_days

    async def create_job(self, request: CreateJobRequest) -> JobRecord:
        job = await self.repository.create(**request.model_dump())
        await self._commit()
        return job

    async def create_uploaded_job(
        self,
        *,
        filename: str,
        business_label: str | None,
        content: bytes,
        content_type: str,
        bucket: str | None = None,
        retention_days: int | None = None,
    ) -> JobRecord:
        if self.storage is None:
            raise RuntimeError("Storage is required for uploaded jobs.")
        file_hash = hashlib.sha256(content).hexdigest()
        key = f"audits/{file_hash[:2]}/{file_hash}-{filename}"
        await self.storage.upload(key=key, content=content, content_type=content_type)
        request = CreateJobRequest(
            filename=filename,
            business_label=business_label,
            file_hash=file_hash,
            s3_bucket=bucket or self.storage_bucket,
            s3_key=key,
            file_size_bytes=len(content),
            content_type=content_type,
            expires_at=datetime.now(timezone.utc) + timedelta(days=retention_days or self.retention_days),
        )
        try:
            job = await self.create_job(request)
        except Exception:
            await self.storage.delete(key=key)
            raise

        try:
            return await self.dispatch_processing(job.id)
        except Exception:
            return await self.fail_processing(job.id, error_message="Failed to dispatch audit job to Celery.")

    async def dispatch_processing(self, job_id: UUID) -> JobRecord:
        job = await self.mark_processing(job_id)
        try:
            celery_app.send_task("app.core.infrastructure.tasks.process_audit_job", args=[str(job_id)])
        except Exception:
            logger.exception(
                "audit job dispatch failed",
                extra={"event": "dispatch_failed", "job_id": str(job_id)},
            )
            await self.fail_processing(job_id, error_message="Failed to dispatch audit job to Celery.")
            raise
        return job

    async def mark_processing(self, job_id: UUID) -> JobRecord:
        job = await self.repository.update(job_id, status=JobStatus.PROCESSING)
        if job is None:
            raise NotFoundError("job")
        await self._commit()
        return job

    async def complete_processing(
        self,
        job_id: UUID,
        *,
        row_count_raw: int,
        row_count_clean: int,
    ) -> JobRecord:
        job = await self.repository.update(
            job_id,
            status=JobStatus.COMPLETED,
            row_count_raw=row_count_raw,
            row_count_clean=row_count_clean,
            completed_at=datetime.now(timezone.utc),
            error_message=None,
        )
        if job is None:
            raise NotFoundError("job")
        await self._commit()
        return job

    async def fail_processing(self, job_id: UUID, *, error_message: str) -> JobRecord:
        job = await self.repository.update(
            job_id,
            status=JobStatus.FAILED,
            completed_at=datetime.now(timezone.utc),
            error_message=error_message,
        )
        if job is None:
            raise NotFoundError("job")
        await self._commit()
        return job

    async def get_job(self, job_id: UUID) -> JobRecord:
        job = await self.repository.get(job_id)
        if job is None:
            raise NotFoundError("job")
        return job

    async def list_jobs(self, *, offset: int, limit: int) -> list[JobRecord]:
        return await self.repository.list(offset=offset, limit=limit)

    async def delete_job(self, job_id: UUID) -> None:
        if not await self.repository.delete(job_id):
            raise NotFoundError("job")
        await self._commit()

    async def _commit(self) -> None:
        session = getattr(self.repository, "session", None)
        if session is not None:
            await session.commit()
