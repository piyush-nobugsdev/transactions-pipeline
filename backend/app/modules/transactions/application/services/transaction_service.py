from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError

from ...domain.entities import TransactionRecord
from ...domain.repositories.transaction_repository import TransactionRepository
from ..dto.request.transaction_requests import CreateTransactionRequest


class TransactionService:
    def __init__(self, repository: TransactionRepository) -> None:
        self.repository = repository

    async def create_transaction(self, request: CreateTransactionRequest) -> TransactionRecord:
        payload = request.model_dump()
        payload["job_id"] = UUID(str(payload["job_id"]))
        transaction = await self.repository.create(**payload)
        return transaction

    async def get_transaction(self, transaction_id: UUID) -> TransactionRecord:
        transaction = await self.repository.get(transaction_id)
        if transaction is None:
            raise NotFoundError("transaction")
        return transaction

    async def list_transactions(self, *, job_id: UUID | None = None, offset: int = 0, limit: int = 50) -> list[TransactionRecord]:
        return await self.repository.list(job_id=job_id, offset=offset, limit=limit)

    async def delete_transaction(self, transaction_id: UUID) -> None:
        if not await self.repository.delete(transaction_id):
            raise NotFoundError("transaction")
