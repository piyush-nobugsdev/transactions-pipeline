from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.modules.transactions.domain.entities import AnomalyReason


class CurrencySpendResponse(BaseModel):
    currency: str
    amount: Decimal
    transaction_count: int


class CategorySpendResponse(BaseModel):
    category: str
    currency: str
    amount: Decimal
    transaction_count: int


class MerchantSpendResponse(BaseModel):
    merchant: str
    transaction_count: int
    currencies: list[CurrencySpendResponse]


class TopTransactionResponse(BaseModel):
    id: UUID
    date: date
    merchant: str
    amount: Decimal
    currency: str
    category: str
    is_anomaly: bool
    anomaly_reason: AnomalyReason | None


class AuditInsightsResponse(BaseModel):
    job_id: UUID
    total_transaction_count: int
    successful_transaction_count: int
    anomaly_count: int
    spending_by_currency: list[CurrencySpendResponse]
    spending_by_category: list[CategorySpendResponse]
    top_transactions: list[TopTransactionResponse]
    repeated_merchants: list[MerchantSpendResponse]
