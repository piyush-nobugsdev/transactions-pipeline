from __future__ import annotations

from ...domain.entities import AnomalyFinding
from ..dto.response.anomaly_responses import AnomalyIssueResponse


def to_anomaly_issue_response(finding: AnomalyFinding) -> AnomalyIssueResponse:
    return AnomalyIssueResponse(
        transaction_id=finding.transaction_id,
        job_id=finding.job_id,
        merchant=finding.merchant,
        amount=finding.amount,
        currency=finding.currency,
        account_id=finding.account_id,
        reason=finding.reason,
        duplicate_of_txn_id=finding.duplicate_of_txn_id,
    )
