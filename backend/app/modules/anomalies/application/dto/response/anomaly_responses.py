from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.transactions.domain.entities import AnomalyReason


class AnomalyIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: UUID
    job_id: UUID
    merchant: str
    amount: Decimal
    currency: str
    account_id: str
    reason: AnomalyReason
    duplicate_of_txn_id: str | None = None


class AnomalyScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    total_transactions: int
    anomaly_count: int
    items: list[AnomalyIssueResponse]
