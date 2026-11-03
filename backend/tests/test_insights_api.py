from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.audits.domain.entities import JobRecord, JobStatus
from app.modules.insights.application.services.insights_service import InsightsService
from app.modules.insights.controllers.dependencies import get_insights_service
from app.modules.transactions.domain.entities import TransactionRecord, TransactionStatus

JOB_ID = UUID("22222222-2222-4222-8222-222222222222")


class InMemoryJobRepository:
    async def get(self, job_id: UUID) -> JobRecord | None:
        if job_id != JOB_ID:
            return None
        return JobRecord(
            id=JOB_ID,
            filename="expenses.csv",
            business_label=None,
            status=JobStatus.COMPLETED,
            file_hash="0" * 64,
            s3_bucket="bucket",
            s3_key="key",
            file_size_bytes=100,
            content_type="text/csv",
            row_count_raw=2,
            row_count_clean=2,
            created_at=date(2026, 11, 1),
            completed_at=None,
            expires_at=date(2026, 12, 1),
            error_message=None,
        )


class InMemoryTransactionRepository:
    def __init__(self) -> None:
        self.transactions = [
            TransactionRecord(
                id=uuid4(),
                job_id=JOB_ID,
                txn_id="txn-1",
                date=date(2026, 11, 1),
                merchant="Amazon",
                amount=Decimal("125.00"),
                currency="USD",
                status=TransactionStatus.SUCCESS,
                category="Office Supplies",
                account_id="account-1",
                is_anomaly=True,
            ),
            TransactionRecord(
                id=uuid4(),
                job_id=JOB_ID,
                txn_id="txn-2",
                date=date(2026, 11, 2),
                merchant="Amazon",
                amount=Decimal("25.00"),
                currency="USD",
                status=TransactionStatus.SUCCESS,
                category="Office Supplies",
                account_id="account-1",
            ),
        ]

    async def list_transactions_for_job(self, job_id: UUID, *, offset: int = 0, limit: int = 500):
        rows = [item for item in self.transactions if item.job_id == job_id]
        return rows[offset : offset + limit]

    async def job_exists(self, job_id: UUID) -> bool:
        return job_id == JOB_ID

    async def update_categories(self, categories: dict[UUID, str]) -> None:
        for transaction in self.transactions:
            if transaction.id in categories:
                transaction.category = categories[transaction.id]


@pytest.fixture
def client():
    service = InsightsService(
        repository=InMemoryTransactionRepository(),
    )
    app.dependency_overrides[get_insights_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_job_insights_returns_spend_categories_and_repeated_merchants(client):
    response = client.get(f"/v1/insights/{JOB_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["total_transaction_count"] == 2
    assert body["successful_transaction_count"] == 2
    assert body["spending_by_currency"] == [
        {"currency": "USD", "amount": "150.00", "transaction_count": 2}
    ]
    assert body["spending_by_category"][0]["category"] == "Office Supplies"
    assert body["repeated_merchants"][0]["merchant"] == "Amazon"
    assert body["repeated_merchants"][0]["transaction_count"] == 2


def test_get_job_insights_returns_not_found_for_unknown_job(client):
    response = client.get(f"/v1/insights/{uuid4()}")

    assert response.status_code == 404
