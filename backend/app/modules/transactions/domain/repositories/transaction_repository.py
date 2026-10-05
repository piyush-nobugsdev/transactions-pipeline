from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ..entities import TransactionRecord


class TransactionRepository(Protocol):
    async def create(self, **data: object) -> TransactionRecord: ...

    async def bulk_create(self, records: list[dict]) -> list[TransactionRecord]: ...

    async def get(self, transaction_id: UUID) -> TransactionRecord | None: ...

    async def list(
        self,
        *,
        job_id: UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[TransactionRecord]: ...

    async def delete(self, transaction_id: UUID) -> bool: ...
