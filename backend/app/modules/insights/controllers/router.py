from uuid import UUID

from fastapi import APIRouter, Depends

from ..application.dto.response.insight_responses import AuditInsightsResponse
from ..application.services.insights_service import InsightsService
from .dependencies import get_insights_service

router = APIRouter(prefix="/v1/insights", tags=["insights"])


@router.get("/{job_id}", response_model=AuditInsightsResponse)
async def get_audit_insights(
    job_id: UUID,
    service: InsightsService = Depends(get_insights_service),
) -> AuditInsightsResponse:
    return await service.get_job_insights(job_id)
