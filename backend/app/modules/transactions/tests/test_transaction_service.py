from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.transactions.application.services.transaction_service import TransactionService
from app.modules.transactions.controllers.dependencies import get_transaction_service
from app.modules.transactions.domain.entities import TransactionRecord
from app.modules.transactions.domain.entities import TransactionStatus


class InMemoryTransactionRepository:
    def __init__(self) -> None:
        self.transactions: dict[UUID, TransactionRecord] = {}

    async def create(self, **data) -> TransactionRecord:
        transaction = TransactionRecord(
            id=uuid4(),
            job_id=data["job_id"],
            txn_id=data.get("txn_id"),
            date=data["date"],
            merchant=data["merchant"],
            amount=data["amount"],
            currency=data["currency"],
            status=data.get("status", TransactionStatus.PENDING),
            category=data.get("category") or "Uncategorised",
            account_id=data["account_id"],
            is_anomaly=data.get("is_anomaly", False),
            anomaly_reason=data.get("anomaly_reason"),
            duplicate_of_txn_id=data.get("duplicate_of_txn_id"),
            llm_category=data.get("llm_category"),
            llm_raw_response=data.get("llm_raw_response"),
            llm_failed=data.get("llm_failed", False),
        )
        self.transactions[transaction.id] = transaction
        return transaction

    async def bulk_create(self, records: list[dict]) -> list[TransactionRecord]:
        created: list[TransactionRecord] = []
        for record in records:
            created.append(await self.create(**record))
        return created

    async def get(self, transaction_id: UUID) -> TransactionRecord | None:
        return self.transactions.get(transaction_id)

    async def list(self, *, job_id: UUID | None = None, offset: int = 0, limit: int = 50) -> list[TransactionRecord]:
        values = list(self.transactions.values())
        if job_id is not None:
            values = [item for item in values if item.job_id == job_id]
        return values[offset : offset + limit]

    async def delete(self, transaction_id: UUID) -> bool:
        return self.transactions.pop(transaction_id, None) is not None


@pytest.fixture
def client():
    repository = InMemoryTransactionRepository()
    app.dependency_overrides[get_transaction_service] = lambda: TransactionService(repository)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def payload() -> dict[str, object]:
    return {
        "job_id": str(uuid4()),
        "txn_id": "txn-001",
        "date": "2026-03-01",
        "merchant": "Amazon",
        "amount": "42.50",
        "currency": "USD",
        "status": "PENDING",
        "category": "Office Supplies",
        "account_id": "acct-001",
        "is_anomaly": False,
    }


def test_create_transaction_returns_201(client, payload):
    response = client.post("/v1/transactions", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["merchant"] == "Amazon"
    assert body["currency"] == "USD"
    assert body["status"] == "PENDING"


def test_list_transactions_by_job_id(client, payload):
    first = client.post("/v1/transactions", json=payload)
    second = client.post("/v1/transactions", json={**payload, "txn_id": "txn-002", "amount": "99.99"})

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(f"/v1/transactions?job_id={payload['job_id']}&offset=0&limit=10")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_delete_transaction_removes_record(client, payload):
    created = client.post("/v1/transactions", json=payload)
    transaction_id = created.json()["id"]

    delete_response = client.delete(f"/v1/transactions/{transaction_id}")
    lookup_response = client.get(f"/v1/transactions/{transaction_id}")

    assert delete_response.status_code == 204
    assert lookup_response.status_code == 404
