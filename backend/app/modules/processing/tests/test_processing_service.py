from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.audits.domain.entities import JobRecord
from app.modules.processing.application.services.processing_service import ProcessingService
from app.modules.audits.domain.entities import JobStatus


class FakeStorage:
    def __init__(self, content: bytes) -> None:
        self.content = content

    async def download(self, *, key: str) -> bytes:
        return self.content


class FakeJobRepository:
    def __init__(self) -> None:
        self.job = JobRecord(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            filename="expenses.csv",
            business_label="Acme",
            status=JobStatus.PROCESSING,
            file_hash="0" * 64,
            s3_bucket="audit-bucket",
            s3_key="audits/expenses.csv",
            file_size_bytes=128,
            content_type="text/csv",
            row_count_raw=0,
            row_count_clean=0,
            created_at=datetime.now(timezone.utc),
            completed_at=None,
            expires_at=datetime.now(timezone.utc),
            error_message=None,
        )
        self.updates: list[dict[str, object]] = []

    async def get(self, job_id: UUID) -> JobRecord | None:
        return self.job if job_id == self.job.id else None

    async def update(self, job_id: UUID, **changes: object) -> JobRecord | None:
        if job_id != self.job.id:
            return None
        self.updates.append(changes)
        for field, value in changes.items():
            setattr(self.job, field, value)
        return self.job


class FakeTransactionRepository:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    async def bulk_create(self, records: list[dict[str, object]]) -> list[dict[str, object]]:
        self.records.extend(records)
        return records


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_processing_cleans_csv_persists_rows_and_completes_job():
    jobs = FakeJobRepository()
    transactions = FakeTransactionRepository()
    unit_of_work = FakeUnitOfWork()
    service = ProcessingService(
        job_repository=jobs,
        transaction_repository=transactions,
        storage=FakeStorage(
            b"txn_id,date,merchant,amount,currency,status,category,account_id\n"
            b"t-1,01-03-2026,Shop,$12.50,usd,SUCCESS,,acct-1\n"
            b"t-1,01-03-2026,Shop,$12.50,usd,SUCCESS,,acct-1\n"
        ),
        unit_of_work=unit_of_work,
    )

    result = await service.process(jobs.job.id)

    assert result.row_count_raw == 2
    assert result.row_count_clean == 1
    assert len(transactions.records) == 1
    assert transactions.records[0]["amount"] == Decimal("12.50")
    assert transactions.records[0]["currency"] == "USD"
    assert transactions.records[0]["category"] == "Uncategorised"
    assert jobs.job.status == JobStatus.COMPLETED
    assert unit_of_work.commits == 2


@pytest.mark.asyncio
async def test_processing_marks_job_failed_when_csv_is_invalid():
    jobs = FakeJobRepository()
    unit_of_work = FakeUnitOfWork()
    service = ProcessingService(
        job_repository=jobs,
        transaction_repository=FakeTransactionRepository(),
        storage=FakeStorage(b"wrong,columns\na,b\n"),
        unit_of_work=unit_of_work,
    )

    with pytest.raises(ValueError, match="missing required columns"):
        await service.process(jobs.job.id)

    assert jobs.job.status == JobStatus.FAILED
    assert jobs.job.error_message is not None
    assert unit_of_work.rollbacks == 1


@pytest.mark.asyncio
async def test_processing_marks_job_failed_when_csv_row_is_short():
    jobs = FakeJobRepository()
    unit_of_work = FakeUnitOfWork()
    service = ProcessingService(
        job_repository=jobs,
        transaction_repository=FakeTransactionRepository(),
        storage=FakeStorage(
            b"txn_id,date,merchant,amount,currency,status,account_id\n"
            b"t-1,2026-03-01,Shop,12.50,USD,SUCCESS\n"
        ),
        unit_of_work=unit_of_work,
    )

    with pytest.raises(ValueError, match="missing values"):
        await service.process(jobs.job.id)

    assert jobs.job.status == JobStatus.FAILED
    assert unit_of_work.rollbacks == 1
