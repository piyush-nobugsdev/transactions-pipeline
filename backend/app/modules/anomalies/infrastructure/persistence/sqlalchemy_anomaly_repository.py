from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transactions.domain.entities import AnomalyReason, TransactionRecord
from app.modules.transactions.infrastructure.persistence.sqlalchemy_transaction_repository import (
    SqlAlchemyTransactionRepository,
)

from ...domain.entities import AnomalyFinding


class AnomalyRepository(Protocol):
    async def list_transactions_for_job(self, job_id: UUID) -> list[TransactionRecord]: ...
    async def bulk_update_anomaly_flags(self, findings: list[AnomalyFinding]) -> None: ...


class SqlAlchemyAnomalyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transaction_repository = SqlAlchemyTransactionRepository(session)

    async def list_transactions_for_job(self, job_id: UUID) -> list[TransactionRecord]:
        return await self.transaction_repository.list(job_id=job_id)

    async def bulk_update_anomaly_flags(self, findings: list[AnomalyFinding]) -> None:
        for finding in findings:
            await self.transaction_repository.update_anomaly_flags(
                finding.transaction_id,
                is_anomaly=True,
                anomaly_reason=finding.reason,
                duplicate_of_txn_id=finding.duplicate_of_txn_id,
            )
