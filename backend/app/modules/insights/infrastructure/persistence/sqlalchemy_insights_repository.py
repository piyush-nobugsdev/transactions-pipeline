from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audits.infrastructure.persistence.sqlalchemy_job_repository import SqlAlchemyJobRepository
from app.modules.transactions.domain.entities import TransactionRecord
from app.modules.transactions.infrastructure.persistence.sqlalchemy_transaction_repository import (
    SqlAlchemyTransactionRepository,
)

from ...domain.repositories.insights_repository import InsightsRepository


class SqlAlchemyInsightsRepository(InsightsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.job_repository = SqlAlchemyJobRepository(session)
        self.transaction_repository = SqlAlchemyTransactionRepository(session)

    async def job_exists(self, job_id: UUID) -> bool:
        return await self.job_repository.get(job_id) is not None

    async def list_transactions_for_job(
        self,
        job_id: UUID,
        *,
        offset: int = 0,
        limit: int = 500,
    ) -> list[TransactionRecord]:
        return await self.transaction_repository.list(
            job_id=job_id,
            offset=offset,
            limit=limit,
        )

    async def update_categories(self, categories: dict[UUID, str]) -> None:
        for transaction_id, category in categories.items():
            updated = await self.transaction_repository.update_category(
                transaction_id,
                category=category,
            )
            if not updated:
                raise RuntimeError("A transaction disappeared during category assignment.")
