from __future__ import annotations

from decimal import Decimal

from app.modules.transactions.domain.entities import AnomalyReason, TransactionRecord

from ..entities import AnomalyFinding

DEFAULT_DOMESTIC_MERCHANTS = {
    "amazon",
    "netflix",
    "uber",
    "lyft",
    "walmart",
    "target",
    "grocery",
    "rent",
    "electric",
    "water",
    "gas",
    "spotify",
    "airbnb",
}


class AnomalyDetector:
    def __init__(
        self,
        *,
        outlier_multiplier: Decimal = Decimal("3.0"),
        domestic_merchants: set[str] | None = None,
    ) -> None:
        self.outlier_multiplier = outlier_multiplier
        self.domestic_merchants = (domestic_merchants or DEFAULT_DOMESTIC_MERCHANTS)

    def detect(self, transactions: list[TransactionRecord]) -> list[AnomalyFinding]:
        findings: list[AnomalyFinding] = []
        flagged_ids: set[str] = set()

        duplicate_findings = self._detect_duplicate_payments(transactions)
        for finding in duplicate_findings:
            flagged_ids.add(str(finding.transaction_id))
            findings.append(finding)

        for transaction in transactions:
            if str(transaction.id) in flagged_ids:
                continue
            outlier_finding = self._detect_outlier(transaction, transactions)
            if outlier_finding is not None:
                flagged_ids.add(str(transaction.id))
                findings.append(outlier_finding)
                continue

            currency_finding = self._detect_currency_mismatch(transaction)
            if currency_finding is not None:
                flagged_ids.add(str(transaction.id))
                findings.append(currency_finding)

        return findings

    def _detect_duplicate_payments(self, transactions: list[TransactionRecord]) -> list[AnomalyFinding]:
        findings: list[AnomalyFinding] = []
        for index, transaction in enumerate(transactions):
            for compare in transactions[index + 1 :]:
                if transaction.account_id != compare.account_id:
                    continue
                if _normalize_merchant(transaction.merchant) != _normalize_merchant(compare.merchant):
                    continue
                if not _is_same_amount_range(transaction.amount, compare.amount):
                    continue
                if abs((transaction.date - compare.date).days) > 3:
                    continue
                if transaction.id == compare.id:
                    continue
                reference = compare.txn_id or str(compare.id)
                findings.append(
                    AnomalyFinding(
                        transaction_id=transaction.id,
                        job_id=transaction.job_id,
                        merchant=transaction.merchant,
                        amount=transaction.amount,
                        currency=transaction.currency,
                        account_id=transaction.account_id,
                        reason=AnomalyReason.DUPLICATE_PAYMENT,
                        duplicate_of_txn_id=reference,
                    )
                )
                findings.append(
                    AnomalyFinding(
                        transaction_id=compare.id,
                        job_id=compare.job_id,
                        merchant=compare.merchant,
                        amount=compare.amount,
                        currency=compare.currency,
                        account_id=compare.account_id,
                        reason=AnomalyReason.DUPLICATE_PAYMENT,
                        duplicate_of_txn_id=transaction.txn_id or str(transaction.id),
                    )
                )
        return findings

    def _detect_outlier(
        self,
        transaction: TransactionRecord,
        transactions: list[TransactionRecord],
    ) -> AnomalyFinding | None:
        candidate_amounts = [
            item.amount
            for item in transactions
            if item.account_id == transaction.account_id and item.id != transaction.id
        ]
        if not candidate_amounts:
            return None
        sorted_amounts = sorted(candidate_amounts)
        length = len(sorted_amounts)
        if length % 2 == 0:
            median = (sorted_amounts[length // 2 - 1] + sorted_amounts[length // 2]) / Decimal(2)
        else:
            median = sorted_amounts[length // 2]
        if transaction.amount > median * self.outlier_multiplier:
            return AnomalyFinding(
                transaction_id=transaction.id,
                job_id=transaction.job_id,
                merchant=transaction.merchant,
                amount=transaction.amount,
                currency=transaction.currency,
                account_id=transaction.account_id,
                reason=AnomalyReason.STATISTICAL_OUTLIER,
            )
        return None

    def _detect_currency_mismatch(self, transaction: TransactionRecord) -> AnomalyFinding | None:
        normalized_merchant = _normalize_merchant(transaction.merchant)
        if transaction.currency.upper() != "USD":
            return None
        if normalized_merchant not in self.domestic_merchants:
            return None
        return AnomalyFinding(
            transaction_id=transaction.id,
            job_id=transaction.job_id,
            merchant=transaction.merchant,
            amount=transaction.amount,
            currency=transaction.currency,
            account_id=transaction.account_id,
            reason=AnomalyReason.CURRENCY_MISMATCH,
        )


def _normalize_merchant(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _is_same_amount_range(left: Decimal, right: Decimal) -> bool:
    if left == 0 or right == 0:
        return False
    percentage_gap = abs(left - right) / max(abs(left), abs(right))
    return percentage_gap <= Decimal("0.01")
