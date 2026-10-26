from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.dependencies import get_db

from ..application.services.anomaly_service import AnomalyDetectionService
from ..infrastructure.persistence.sqlalchemy_anomaly_repository import SqlAlchemyAnomalyRepository


def get_anomaly_service(
    session: AsyncSession = Depends(get_db),
) -> AnomalyDetectionService:
    repository = SqlAlchemyAnomalyRepository(session)
    return AnomalyDetectionService(repository=repository)
