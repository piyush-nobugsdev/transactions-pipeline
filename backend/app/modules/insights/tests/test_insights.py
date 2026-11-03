from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.modules.audits.domain.entities import JobRecord, JobStatus
from app.modules.insights.application.services.insights_service import InsightsService
from app.modules.insights.domain.services.category_classifier import (
    CategoryClassifier,
    ExpenseCategory,
)
from app.modules.insights.domain.services.insight_calculator import InsightCalculator
from app.modules.transactions.domain.entities import TransactionRecord, TransactionStatus

JOB_ID = UUID("22222222-2222-4222-8222-222222222222")


def _transaction(
    merchant: str,
    amount: str,
    currency: str,
    *,
    category: str = "Uncategorised",
    status: TransactionStatus = TransactionStatus.SUCCESS,
) -> TransactionRecord:
    return TransactionRecord(
        id=uuid4(),
        job_id=JOB_ID,
        txn_id=None,
        date=date(2026, 11, 1),
        merchant=merchant,
        amount=Decimal(amount),
        currency=currency,
        status=status,
        category=category,
        account_id="account-1",
    )


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
            row_count_raw=4,
            row_count_clean=4,
            created_at=datetime(2026, 11, 1, tzinfo=UTC),
            completed_at=None,
            expires_at=datetime(2026, 12, 1, tzinfo=UTC),
            error_message=None,
        )


class InMemoryTransactionRepository:
    def __init__(self, transactions: list[TransactionRecord]) -> None:
        self.transactions = transactions

    async def list(self, *, job_id: UUID | None = None, offset: int = 0, limit: int = 50):
        matching = [item for item in self.transactions if item.job_id == job_id]
        return matching[offset : offset + limit]

    async def bulk_update_categories(self, categories: dict[UUID, str]) -> None:
        for transaction in self.transactions:
            if transaction.id in categories:
                transaction.category = categories[transaction.id]


class InMemoryInsightsRepository:
    def __init__(
        self,
        jobs: InMemoryJobRepository,
        transactions: InMemoryTransactionRepository,
    ) -> None:
        self.jobs = jobs
        self.transactions = transactions

    async def job_exists(self, job_id: UUID) -> bool:
        return await self.jobs.get(job_id) is not None

    async def list_transactions_for_job(self, job_id: UUID, *, offset: int = 0, limit: int = 500):
        return await self.transactions.list(job_id=job_id, offset=offset, limit=limit)

    async def update_categories(self, categories: dict[UUID, str]) -> None:
        await self.transactions.bulk_update_categories(categories)


def test_category_classifier_maps_common_merchants_and_has_other_fallback():
    classifier = CategoryClassifier()

    assert classifier.classify("Amazon Marketplace") == ExpenseCategory.OFFICE_SUPPLIES
    assert classifier.classify("Netflix monthly subscription") == ExpenseCategory.SOFTWARE_SUBSCRIPTIONS
    assert classifier.classify("Some Local Shop") == ExpenseCategory.OTHER


def test_insight_calculator_keeps_currencies_separate_and_counts_successful_spend():
    transactions = [
        _transaction("Acme Cafe", "25.00", "USD"),
        _transaction("Acme Cafe", "35.00", "USD"),
        _transaction("Acme Cafe", "3000.00", "INR"),
        _transaction("Acme Cafe", "999.00", "USD", status=TransactionStatus.FAILED),
    ]

    insights = InsightCalculator().calculate(JOB_ID, transactions)

    assert insights.total_transaction_count == 4
    assert insights.successful_transaction_count == 3
    assert [(item.currency, item.amount) for item in insights.spending_by_currency] == [
        ("INR", Decimal("3000.00")),
        ("USD", Decimal("60.00")),
    ]
    assert insights.repeated_merchants[0].transaction_count == 3
    assert len(insights.top_transactions) == 3
    assert all(item.currency in {"USD", "INR"} for item in insights.top_transactions)


@pytest.mark.asyncio
async def test_insights_service_classifies_only_uncategorised_transactions():
    transactions = [
        _transaction("Amazon", "25.00", "USD"),
        _transaction("Unknown Merchant", "15.00", "USD", category="Travel"),
    ]
    repository = InMemoryTransactionRepository(transactions)
    service = InsightsService(
        repository=InMemoryInsightsRepository(InMemoryJobRepository(), repository),
    )

    await service.categorize_and_persist(transactions)

    assert transactions[0].category == ExpenseCategory.OFFICE_SUPPLIES.value
    assert transactions[1].category == "Travel"


@pytest.mark.asyncio
async def test_insights_service_rejects_missing_job():
    service = InsightsService(
        repository=InMemoryInsightsRepository(
            InMemoryJobRepository(),
            InMemoryTransactionRepository([]),
        ),
    )

    with pytest.raises(NotFoundError):
        await service.get_job_insights(uuid4())
