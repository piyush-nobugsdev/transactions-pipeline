from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.transactions.domain.entities import TransactionRecord


class InsightsRepository(Protocol):
    async def job_exists(self, job_id: UUID) -> bool: ...

    async def list_transactions_for_job(
        self,
        job_id: UUID,
        *,
        offset: int = 0,
        limit: int = 500,
    ) -> list[TransactionRecord]: ...

    async def update_categories(self, categories: dict[UUID, str]) -> None: ...
