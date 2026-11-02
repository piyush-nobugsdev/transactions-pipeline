from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.audits.application.services.audit_results_service import AuditResultsService
from app.modules.audits.controllers.dependencies import get_audit_results_service
from app.modules.audits.domain.entities import JobRecord, JobStatus
from app.modules.transactions.domain.entities import (
    AnomalyReason,
    TransactionRecord,
    TransactionStatus,
)


class InMemoryJobRepository:
    def __init__(self, job: JobRecord | None) -> None:
        self.job = job

    async def get(self, job_id: UUID) -> JobRecord | None:
        return self.job if self.job is not None and self.job.id == job_id else None


class InMemoryTransactionRepository:
    def __init__(self, transactions: list[TransactionRecord]) -> None:
        self.transactions = transactions

    async def list(
        self,
        *,
        job_id: UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[TransactionRecord]:
        rows = [item for item in self.transactions if item.job_id == job_id]
        return rows[offset : offset + limit]

    async def count(self, *, job_id: UUID) -> int:
        return sum(item.job_id == job_id for item in self.transactions)

    async def count_anomalies(self, *, job_id: UUID) -> int:
        return sum(
            item.job_id == job_id and item.is_anomaly
            for item in self.transactions
        )


def _job(job_id: UUID) -> JobRecord:
    return JobRecord(
        id=job_id,
        filename="expenses.csv",
        business_label="Acme",
        status=JobStatus.COMPLETED,
        file_hash="0" * 64,
        s3_bucket="audit-bucket",
        s3_key="audits/expenses.csv",
        file_size_bytes=128,
        content_type="text/csv",
        row_count_raw=3,
        row_count_clean=2,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        error_message=None,
    )


def _transaction(job_id: UUID, *, is_anomaly: bool = False) -> TransactionRecord:
    return TransactionRecord(
        id=uuid4(),
        job_id=job_id,
        txn_id="txn-1",
        date=date(2026, 3, 1),
        merchant="Coffee Shop",
        amount=Decimal("12.50"),
        currency="USD",
        status=TransactionStatus.SUCCESS,
        category="Meals",
        account_id="acct-1",
        is_anomaly=is_anomaly,
        anomaly_reason=AnomalyReason.CURRENCY_MISMATCH if is_anomaly else None,
    )


@pytest.fixture
def client():
    job_id = UUID("00000000-0000-0000-0000-000000000001")
    transactions = [_transaction(job_id), _transaction(job_id, is_anomaly=True)]
    service = AuditResultsService(
        job_repository=InMemoryJobRepository(_job(job_id)),
        transaction_repository=InMemoryTransactionRepository(transactions),
    )
    app.dependency_overrides[get_audit_results_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_audit_results_returns_paginated_transactions_and_anomaly_count(client):
    response = client.get(
        "/v1/audits/00000000-0000-0000-0000-000000000001/results?offset=1&limit=1"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["row_count_raw"] == 3
    assert body["row_count_clean"] == 2
    assert body["total_transactions"] == 2
    assert body["anomaly_count"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["is_anomaly"] is True
    assert body["offset"] == 1
    assert body["limit"] == 1


def test_get_audit_results_returns_not_found_for_unknown_job(client):
    response = client.get("/v1/audits/00000000-0000-0000-0000-000000000099/results")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
