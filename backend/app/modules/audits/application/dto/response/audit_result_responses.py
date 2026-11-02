from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.audits.domain.entities import JobStatus
from app.modules.transactions.domain.entities import AnomalyReason, TransactionStatus


class AuditResultTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
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


class AuditResultsResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    row_count_raw: int
    row_count_clean: int
    total_transactions: int
    anomaly_count: int
    items: list[AuditResultTransactionResponse]
    offset: int
    limit: int
