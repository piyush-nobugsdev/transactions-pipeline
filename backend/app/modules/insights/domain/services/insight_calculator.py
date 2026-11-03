from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from app.modules.transactions.domain.entities import TransactionRecord, TransactionStatus

from ..entities import (
    AuditInsights,
    CategorySpend,
    CurrencySpend,
    MerchantSpend,
    TopTransaction,
)


class InsightCalculator:
    def calculate(
        self,
        job_id: UUID,
        transactions: list[TransactionRecord],
        *,
        top_limit: int = 5,
    ) -> AuditInsights:
        successful = [item for item in transactions if item.status == TransactionStatus.SUCCESS]
        currency_totals: dict[str, list[Decimal | int]] = defaultdict(lambda: [Decimal(0), 0])
        category_totals: dict[tuple[str, str], list[Decimal | int]] = defaultdict(lambda: [Decimal(0), 0])
        merchant_totals: dict[str, dict[str, list[Decimal | int]]] = defaultdict(
            lambda: defaultdict(lambda: [Decimal(0), 0])
        )

        for transaction in successful:
            currency = transaction.currency.upper()
            currency_totals[currency][0] += transaction.amount
            currency_totals[currency][1] += 1

            category_key = (transaction.category, currency)
            category_totals[category_key][0] += transaction.amount
            category_totals[category_key][1] += 1

            merchant_key = _normalize_merchant(transaction.merchant)
            merchant_currency = merchant_totals[merchant_key][currency]
            merchant_currency[0] += transaction.amount
            merchant_currency[1] += 1

        spending_by_currency = tuple(
            CurrencySpend(currency, values[0], values[1])
            for currency, values in sorted(currency_totals.items())
        )
        spending_by_category = tuple(
            CategorySpend(category, currency, values[0], values[1])
            for (category, currency), values in sorted(category_totals.items())
        )
        repeated_merchants = []
        for merchant_key, currencies in merchant_totals.items():
            transaction_count = sum(values[1] for values in currencies.values())
            if transaction_count < 2:
                continue
            repeated_merchants.append(
                MerchantSpend(
                    merchant=next(
                        item.merchant
                        for item in successful
                        if _normalize_merchant(item.merchant) == merchant_key
                    ),
                    transaction_count=transaction_count,
                    currencies=tuple(
                        CurrencySpend(currency, values[0], values[1])
                        for currency, values in sorted(currencies.items())
                    ),
                )
            )
        repeated_merchants.sort(key=lambda item: (-item.transaction_count, item.merchant.lower()))

        top_transactions = []
        for currency in sorted({item.currency.upper() for item in successful}):
            currency_transactions = sorted(
                (item for item in successful if item.currency.upper() == currency),
                key=lambda item: (-item.amount, item.date, str(item.id)),
            )
            top_transactions.extend(
                TopTransaction(
                    id=item.id,
                    date=item.date,
                    merchant=item.merchant,
                    amount=item.amount,
                    currency=item.currency.upper(),
                    category=item.category,
                    is_anomaly=item.is_anomaly,
                    anomaly_reason=item.anomaly_reason,
                )
                for item in currency_transactions[:top_limit]
            )

        return AuditInsights(
            job_id=job_id,
            total_transaction_count=len(transactions),
            successful_transaction_count=len(successful),
            anomaly_count=sum(item.is_anomaly for item in transactions),
            spending_by_currency=spending_by_currency,
            spending_by_category=spending_by_category,
            top_transactions=tuple(top_transactions),
            repeated_merchants=tuple(repeated_merchants[:top_limit]),
        )


def _normalize_merchant(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())
