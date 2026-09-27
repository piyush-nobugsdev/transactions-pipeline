from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.schemas.models import AnomalyReason, TransactionStatus


@dataclass(slots=True)
class TransactionRecord:
    id: UUID
    job_id: UUID
    txn_id: str | None
    date: date
    merchant: str
    amount: Decimal
    currency: str
    status: TransactionStatus
    category: str
    account_id: str
    is_anomaly: bool = False
    anomaly_reason: AnomalyReason | None = None
    duplicate_of_txn_id: str | None = None
    llm_category: str | None = None
    llm_raw_response: str | None = None
    llm_failed: bool = False
