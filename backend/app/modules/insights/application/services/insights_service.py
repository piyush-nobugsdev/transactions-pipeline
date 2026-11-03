from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.modules.transactions.domain.entities import TransactionRecord

from ...domain.entities import AuditInsights
from ...domain.repositories.insights_repository import InsightsRepository
from ...domain.services.category_classifier import CategoryClassifier
from ...domain.services.insight_calculator import InsightCalculator
from ..dto.response.insight_responses import AuditInsightsResponse


class InsightsService:
    def __init__(
        self,
        *,
        repository: InsightsRepository,
        category_classifier: CategoryClassifier | None = None,
        insight_calculator: InsightCalculator | None = None,
    ) -> None:
        self.repository = repository
        self.category_classifier = category_classifier or CategoryClassifier()
        self.insight_calculator = insight_calculator or InsightCalculator()

    async def categorize_and_persist(self, transactions: list[TransactionRecord]) -> None:
        category_updates = {}
        for transaction in transactions:
            if transaction.category.strip().lower() in {"", "uncategorised", "uncategorized"}:
                transaction.category = self.category_classifier.classify(transaction.merchant).value
                category_updates[transaction.id] = transaction.category
        if category_updates:
            await self.repository.update_categories(category_updates)

    async def get_job_insights(self, job_id: UUID) -> AuditInsightsResponse:
        if not await self.repository.job_exists(job_id):
            raise NotFoundError("job")

        transactions: list[TransactionRecord] = []
        offset = 0
        page_size = 500
        while page := await self.repository.list_transactions_for_job(
            job_id=job_id,
            offset=offset,
            limit=page_size,
        ):
            transactions.extend(page)
            offset += len(page)

        insights = self.insight_calculator.calculate(job_id, transactions)
        return _to_response(insights)


def _to_response(insights: AuditInsights) -> AuditInsightsResponse:
    return AuditInsightsResponse(
        job_id=insights.job_id,
        total_transaction_count=insights.total_transaction_count,
        successful_transaction_count=insights.successful_transaction_count,
        anomaly_count=insights.anomaly_count,
        spending_by_currency=[
            {
                "currency": item.currency,
                "amount": item.amount,
                "transaction_count": item.transaction_count,
            }
            for item in insights.spending_by_currency
        ],
        spending_by_category=[
            {
                "category": item.category,
                "currency": item.currency,
                "amount": item.amount,
                "transaction_count": item.transaction_count,
            }
            for item in insights.spending_by_category
        ],
        top_transactions=[
            {
                "id": item.id,
                "date": item.date,
                "merchant": item.merchant,
                "amount": item.amount,
                "currency": item.currency,
                "category": item.category,
                "is_anomaly": item.is_anomaly,
                "anomaly_reason": item.anomaly_reason,
            }
            for item in insights.top_transactions
        ],
        repeated_merchants=[
            {
                "merchant": item.merchant,
                "transaction_count": item.transaction_count,
                "currencies": [
                    {
                        "currency": currency.currency,
                        "amount": currency.amount,
                        "transaction_count": currency.transaction_count,
                    }
                    for currency in item.currencies
                ],
            }
            for item in insights.repeated_merchants
        ],
    )
