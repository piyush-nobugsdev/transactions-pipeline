from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.anomalies.domain.services.anomaly_detector import AnomalyDetector
from app.modules.transactions.domain.entities import AnomalyReason, TransactionRecord, TransactionStatus


def _record(**overrides):
    data = {
        "id": overrides.pop("id", UUID("11111111-1111-4111-8111-111111111111")),
        "job_id": overrides.pop("job_id", UUID("22222222-2222-4222-8222-222222222222")),
        "txn_id": overrides.pop("txn_id", "txn-1"),
        "date": overrides.pop("date", date(2026, 1, 10)),
        "merchant": overrides.pop("merchant", "Amazon"),
        "amount": overrides.pop("amount", Decimal("100.00")),
        "currency": overrides.pop("currency", "USD"),
        "status": overrides.pop("status", TransactionStatus.PENDING),
        "category": overrides.pop("category", "Shopping"),
        "account_id": overrides.pop("account_id", "acct-1"),
        "is_anomaly": overrides.pop("is_anomaly", False),
        "anomaly_reason": overrides.pop("anomaly_reason", None),
        "duplicate_of_txn_id": overrides.pop("duplicate_of_txn_id", None),
        "llm_category": overrides.pop("llm_category", None),
        "llm_raw_response": overrides.pop("llm_raw_response", None),
        "llm_failed": overrides.pop("llm_failed", False),
    }
    return TransactionRecord(**data)


def test_duplicate_payment_is_detected():
    first = _record(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        txn_id="txn-1",
        date=date(2026, 1, 10),
        merchant="Amazon",
        amount=Decimal("100.00"),
        account_id="acct-1",
    )
    second = _record(
        id=UUID("11111111-1111-4111-8111-111111111112"),
        txn_id="txn-2",
        date=date(2026, 1, 12),
        merchant="Amazon",
        amount=Decimal("99.50"),
        account_id="acct-1",
    )

    findings = AnomalyDetector().detect([first, second])

    assert any(item.reason == AnomalyReason.DUPLICATE_PAYMENT for item in findings)


def test_outlier_is_detected_for_account():
    first = _record(id=UUID("11111111-1111-4111-8111-111111111111"), amount=Decimal("50.00"), account_id="acct-1")
    second = _record(id=UUID("11111111-1111-4111-8111-111111111112"), amount=Decimal("55.00"), account_id="acct-1")
    third = _record(id=UUID("11111111-1111-4111-8111-111111111113"), amount=Decimal("300.00"), account_id="acct-1")

    findings = AnomalyDetector().detect([first, second, third])

    assert any(item.reason == AnomalyReason.STATISTICAL_OUTLIER for item in findings)


def test_currency_mismatch_is_detected_for_domestic_merchant():
    transaction = _record(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        merchant="Amazon",
        amount=Decimal("25.00"),
        currency="USD",
        account_id="acct-1",
    )

    findings = AnomalyDetector().detect([transaction])

    assert any(item.reason == AnomalyReason.CURRENCY_MISMATCH for item in findings)
