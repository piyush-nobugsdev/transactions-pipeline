from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_db

from ..application.services.transaction_service import TransactionService
from ..infrastructure.persistence.sqlalchemy_transaction_repository import SqlAlchemyTransactionRepository


def get_transaction_service(
    session: AsyncSession = Depends(get_db),
) -> TransactionService:
    return TransactionService(SqlAlchemyTransactionRepository(session))
