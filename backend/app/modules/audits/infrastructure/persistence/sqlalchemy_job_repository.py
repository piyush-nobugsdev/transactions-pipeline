from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.schemas.models import Job

from ..mappers.job_mapper import to_domain
from ...domain.entities import JobRecord, JobStatus


class SqlAlchemyJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        filename: str,
        business_label: str | None,
        file_hash: str,
        s3_bucket: str,
        s3_key: str,
        file_size_bytes: int,
        content_type: str,
        expires_at: datetime,
    ) -> JobRecord:
        job = Job(
            filename=filename,
            business_label=business_label,
            status=JobStatus.PENDING,
            file_hash=file_hash,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            file_size_bytes=file_size_bytes,
            content_type=content_type,
            expires_at=expires_at,
        )
        self.session.add(job)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A job with this business label and file already exists.") from exc
        return to_domain(job)

    async def get(self, job_id: UUID) -> JobRecord | None:
        job = await self.session.get(Job, job_id)
        return to_domain(job) if job is not None else None

    async def list(self, *, offset: int, limit: int) -> list[JobRecord]:
        statement = select(Job).order_by(Job.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(statement)
        return [to_domain(job) for job in result.scalars().all()]

    async def update(self, job_id: UUID, **changes: object) -> JobRecord | None:
        job = await self.session.get(Job, job_id)
        if job is None:
            return None
        for field, value in changes.items():
            setattr(job, field, value)
        await self.session.flush()
        return to_domain(job)

    async def delete(self, job_id: UUID) -> bool:
        result = await self.session.execute(delete(Job).where(Job.id == job_id))
        return result.rowcount > 0
