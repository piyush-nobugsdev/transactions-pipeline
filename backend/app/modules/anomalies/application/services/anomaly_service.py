from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.modules.transactions.domain.entities import TransactionRecord

from ...domain.entities import AnomalyFinding
from ...domain.repositories.anomaly_repository import AnomalyRepository
from ...domain.services.anomaly_detector import AnomalyDetector


class AnomalyDetectionService:
    def __init__(
        self,
        *,
        repository: AnomalyRepository,
        outlier_multiplier: Decimal = Decimal("3.0"),
        domestic_merchants: set[str] | None = None,
    ) -> None:
        self.repository = repository
        self.detector = AnomalyDetector(
            outlier_multiplier=outlier_multiplier,
            domestic_merchants=domestic_merchants,
        )

    async def scan_job(self, job_id: UUID) -> tuple[list[TransactionRecord], list[AnomalyFinding]]:
        transactions: list[TransactionRecord] = []
        offset = 0
        page_size = 500
        while page := await self.repository.list_transactions_for_job(
            job_id,
            offset=offset,
            limit=page_size,
        ):
            transactions.extend(page)
            offset += len(page)

        if not transactions:
            raise NotFoundError("job")

        findings = await self.analyze_transactions(transactions)
        if hasattr(self.repository, "session"):
            await self.repository.session.commit()
        return transactions, findings

    async def analyze_and_persist(self, transactions: list[TransactionRecord]) -> None:
        await self.analyze_transactions(transactions)

    async def analyze_transactions(
        self,
        transactions: list[TransactionRecord],
    ) -> list[AnomalyFinding]:
        findings = self.detector.detect(transactions)
        await self.repository.bulk_update_anomaly_flags(findings)
        return findings

    def summarize(
        self,
        job_id: UUID,
        transactions: list[TransactionRecord],
        findings: list[AnomalyFinding],
    ) -> dict[str, object]:
        return {
            "job_id": job_id,
            "total_transactions": len(transactions),
            "anomaly_count": len(findings),
            "items": findings,
        }
