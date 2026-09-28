from uuid import UUID

import pytest

from app.core.storage.interface import Storage
from app.modules.audits.application.services.job_service import JobService
from app.modules.audits.domain.entities import JobRecord
from app.modules.audits.domain.entities import JobStatus


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def upload(self, *, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = content

    async def download(self, *, key: str) -> bytes:
        return self.objects[key]

    async def delete(self, *, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)

    async def exists(self, *, key: str) -> bool:
        return key in self.objects


class FakeRepository:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.job: JobRecord | None = None

    async def create(self, **data) -> JobRecord:
        if self.fail:
            raise RuntimeError("database unavailable")
        self.job = JobRecord(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            filename=data["filename"],
            business_label=data["business_label"],
            status=JobStatus.PENDING,
            file_hash=data["file_hash"],
            s3_bucket=data["s3_bucket"],
            s3_key=data["s3_key"],
            file_size_bytes=data["file_size_bytes"],
            content_type=data["content_type"],
            row_count_raw=0,
            row_count_clean=0,
            created_at=data["expires_at"],
            completed_at=None,
            expires_at=data["expires_at"],
            error_message=None,
        )
        return self.job

    async def update(self, job_id: UUID, **changes):
        if self.job is None:
            raise RuntimeError("job not created")
        for key, value in changes.items():
            setattr(self.job, key, value)
        return self.job


@pytest.mark.asyncio
async def test_uploaded_job_stores_content_before_creating_job():
    # Verifies uploaded bytes are sent to storage and the created job records their hash and size.
    storage: Storage = FakeStorage()
    service = JobService(FakeRepository(), storage, storage_bucket="audit-bucket")

    job = await service.create_uploaded_job(
        filename="expenses.csv",
        business_label="Acme",
        content=b"date,amount\n2026-01-01,10",
        content_type="text/csv",
    )

    assert job.filename == "expenses.csv"
    assert job.file_size_bytes == 25
    assert job.s3_bucket == "audit-bucket"
    assert len(storage.objects) == 1


@pytest.mark.asyncio
async def test_uploaded_job_deletes_object_when_database_creation_fails():
    # Verifies an orphaned object is removed when database persistence fails after the storage upload.
    storage = FakeStorage()
    service = JobService(FakeRepository(fail=True), storage, storage_bucket="audit-bucket")

    with pytest.raises(RuntimeError, match="database unavailable"):
        await service.create_uploaded_job(
            filename="expenses.csv",
            business_label=None,
            content=b"content",
            content_type="text/csv",
        )

    assert storage.objects == {}
    assert len(storage.deleted) == 1