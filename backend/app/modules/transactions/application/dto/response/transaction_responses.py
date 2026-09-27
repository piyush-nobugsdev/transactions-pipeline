from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.models import AnomalyReason, TransactionStatus


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    is_anomaly: bool
    anomaly_reason: AnomalyReason | None
    duplicate_of_txn_id: str | None
    llm_category: str | None
    llm_raw_response: str | None
    llm_failed: bool


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    offset: int
    limit: int
