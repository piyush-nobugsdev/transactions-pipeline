from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.transactions.domain.entities import TransactionRecord

from ..entities import AnomalyFinding


class AnomalyRepository(Protocol):
    async def list_transactions_for_job(self, job_id: UUID) -> list[TransactionRecord]: ...
    async def bulk_update_anomaly_flags(self, findings: list[AnomalyFinding]) -> None: ...
