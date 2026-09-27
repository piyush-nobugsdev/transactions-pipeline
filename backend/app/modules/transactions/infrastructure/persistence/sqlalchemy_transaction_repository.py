from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.schemas.models import Transaction

from ...domain.entities import TransactionRecord


class SqlAlchemyTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **data: object) -> TransactionRecord:
        transaction = Transaction(
            job_id=data["job_id"],
            txn_id=data.get("txn_id"),
            date=data["date"],
            merchant=data["merchant"],
            amount=data["amount"],
            currency=data["currency"],
            status=data.get("status"),
            category=data.get("category", "Uncategorised"),
            account_id=data["account_id"],
            is_anomaly=data.get("is_anomaly", False),
            anomaly_reason=data.get("anomaly_reason"),
            duplicate_of_txn_id=data.get("duplicate_of_txn_id"),
            llm_category=data.get("llm_category"),
            llm_raw_response=data.get("llm_raw_response"),
            llm_failed=data.get("llm_failed", False),
        )
        self.session.add(transaction)
        try:
            await self.session.flush()
        except Exception as exc:
            await self.session.rollback()
            raise ConflictError("The transaction could not be saved.") from exc
        return self._to_domain(transaction)

    async def bulk_create(self, records: list[dict]) -> list[TransactionRecord]:
        created: list[TransactionRecord] = []
        for record in records:
            created.append(await self.create(**record))
        return created

    async def get(self, transaction_id: UUID) -> TransactionRecord | None:
        transaction = await self.session.get(Transaction, transaction_id)
        if transaction is None:
            return None
        return self._to_domain(transaction)

    async def list(self, *, job_id: UUID | None = None, offset: int = 0, limit: int = 50) -> list[TransactionRecord]:
        statement = select(Transaction)
        if job_id is not None:
            statement = statement.where(Transaction.job_id == job_id)
        statement = statement.order_by(Transaction.date.desc()).offset(offset).limit(limit)
        result = await self.session.execute(statement)
        return [self._to_domain(transaction) for transaction in result.scalars().all()]

    async def delete(self, transaction_id: UUID) -> bool:
        result = await self.session.execute(delete(Transaction).where(Transaction.id == transaction_id))
        return result.rowcount > 0

    def _to_domain(self, transaction: Transaction) -> TransactionRecord:
        return TransactionRecord(
            id=transaction.id,
            job_id=transaction.job_id,
            txn_id=transaction.txn_id,
            date=transaction.date,
            merchant=transaction.merchant,
            amount=transaction.amount,
            currency=transaction.currency,
            status=transaction.status,
            category=transaction.category,
            account_id=transaction.account_id,
            is_anomaly=transaction.is_anomaly,
            anomaly_reason=transaction.anomaly_reason,
            duplicate_of_txn_id=transaction.duplicate_of_txn_id,
            llm_category=transaction.llm_category,
            llm_raw_response=transaction.llm_raw_response,
            llm_failed=transaction.llm_failed,
        )
