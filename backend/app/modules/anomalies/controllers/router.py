from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..application.dto.request.anomaly_requests import ScanAnomaliesRequest
from ..application.dto.response.anomaly_responses import AnomalyIssueResponse, AnomalyScanResponse
from ..application.services.anomaly_service import AnomalyDetectionService
from .dependencies import get_anomaly_service

router = APIRouter(prefix="/v1/anomalies", tags=["anomalies"])


@router.post("/scan", response_model=AnomalyScanResponse, status_code=status.HTTP_200_OK)
async def scan_anomalies(
    request: ScanAnomaliesRequest,
    service: AnomalyDetectionService = Depends(get_anomaly_service),
) -> AnomalyScanResponse:
    service.detector.outlier_multiplier = request.outlier_multiplier
    transactions = await service.repository.list_transactions_for_job(request.job_id)
    findings = await service.scan_job(request.job_id)
    payload = service.summarize(request.job_id, transactions, findings)
    return AnomalyScanResponse(
        job_id=request.job_id,
        total_transactions=payload["total_transactions"],
        anomaly_count=payload["anomaly_count"],
        items=[
            AnomalyIssueResponse(
                transaction_id=item.transaction_id,
                job_id=item.job_id,
                merchant=item.merchant,
                amount=item.amount,
                currency=item.currency,
                account_id=item.account_id,
                reason=item.reason,
                duplicate_of_txn_id=item.duplicate_of_txn_id,
            )
            for item in findings
        ],
    )


@router.get("", response_model=AnomalyScanResponse)
async def list_anomalies(
    job_id: UUID = Query(...),
    service: AnomalyDetectionService = Depends(get_anomaly_service),
) -> AnomalyScanResponse:
    transactions = await service.repository.list_transactions_for_job(job_id)
    findings = await service.scan_job(job_id)
    payload = service.summarize(job_id, transactions, findings)
    return AnomalyScanResponse(
        job_id=job_id,
        total_transactions=payload["total_transactions"],
        anomaly_count=payload["anomaly_count"],
        items=[
            AnomalyIssueResponse(
                transaction_id=item.transaction_id,
                job_id=item.job_id,
                merchant=item.merchant,
                amount=item.amount,
                currency=item.currency,
                account_id=item.account_id,
                reason=item.reason,
                duplicate_of_txn_id=item.duplicate_of_txn_id,
            )
            for item in findings
        ],
    )
