from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.transactions.domain.entities import AnomalyReason


@dataclass(frozen=True, slots=True)
class CurrencySpend:
    currency: str
    amount: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class CategorySpend:
    category: str
    currency: str
    amount: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class MerchantSpend:
    merchant: str
    transaction_count: int
    currencies: tuple[CurrencySpend, ...]


@dataclass(frozen=True, slots=True)
class TopTransaction:
    id: UUID
    date: date
    merchant: str
    amount: Decimal
    currency: str
    category: str
    is_anomaly: bool
    anomaly_reason: AnomalyReason | None


@dataclass(frozen=True, slots=True)
class AuditInsights:
    job_id: UUID
    total_transaction_count: int
    successful_transaction_count: int
    anomaly_count: int
    spending_by_currency: tuple[CurrencySpend, ...]
    spending_by_category: tuple[CategorySpend, ...]
    top_transactions: tuple[TopTransaction, ...]
    repeated_merchants: tuple[MerchantSpend, ...]
