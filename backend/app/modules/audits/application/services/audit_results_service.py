from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.modules.transactions.domain.repositories.transaction_repository import TransactionRepository

from ...domain.repositories.job_repository import JobRepository
from ..dto.response.audit_result_responses import (
    AuditResultsResponse,
    AuditResultTransactionResponse,
)


class AuditResultsService:
    def __init__(
        self,
        *,
        job_repository: JobRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self.job_repository = job_repository
        self.transaction_repository = transaction_repository

    async def get_results(self, job_id: UUID, *, offset: int, limit: int) -> AuditResultsResponse:
        job = await self.job_repository.get(job_id)
        if job is None:
            raise NotFoundError("job")

        transactions = await self.transaction_repository.list(
            job_id=job_id,
            offset=offset,
            limit=limit,
        )
        return AuditResultsResponse(
            job_id=job.id,
            status=job.status,
            row_count_raw=job.row_count_raw,
            row_count_clean=job.row_count_clean,
            total_transactions=await self.transaction_repository.count(job_id=job_id),
            anomaly_count=await self.transaction_repository.count_anomalies(job_id=job_id),
            items=[AuditResultTransactionResponse.model_validate(item) for item in transactions],
            offset=offset,
            limit=limit,
        )
