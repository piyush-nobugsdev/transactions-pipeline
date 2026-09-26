from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database.dependencies import get_db
from app.core.storage.dependencies import get_storage
from app.core.storage.interface import Storage

from ..application.services.job_service import JobService
from ..infrastructure.persistence.sqlalchemy_job_repository import SqlAlchemyJobRepository


def get_job_service(
    session: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> JobService:
    return JobService(
        SqlAlchemyJobRepository(session),
        storage,
        storage_bucket=settings.S3_BUCKET_NAME,
        retention_days=settings.JOB_RETENTION_DAYS,
    )
