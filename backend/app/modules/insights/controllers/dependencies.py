from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_db

from ..application.services.insights_service import InsightsService
from ..infrastructure.persistence.sqlalchemy_insights_repository import SqlAlchemyInsightsRepository


def get_insights_service(session: AsyncSession = Depends(get_db)) -> InsightsService:
    return InsightsService(repository=SqlAlchemyInsightsRepository(session))
