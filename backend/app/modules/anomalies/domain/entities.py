from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.transactions.domain.entities import AnomalyReason


@dataclass(slots=True)
class AnomalyFinding:
    transaction_id: UUID
    job_id: UUID
    merchant: str
    amount: Decimal
    currency: str
    account_id: str
    reason: AnomalyReason
    duplicate_of_txn_id: str | None = None
