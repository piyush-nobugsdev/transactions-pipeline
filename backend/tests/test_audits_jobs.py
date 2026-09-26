from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.audits.controllers.dependencies import get_job_service
from app.modules.audits.domain.entities import JobRecord
from app.modules.audits.application.services.job_service import JobService
from app.schemas.models import JobStatus


class InMemoryJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[UUID, JobRecord] = {}

    async def create(self, **data) -> JobRecord:
        job = JobRecord(
            id=uuid4(),
            filename=data["filename"],
            business_label=data["business_label"],
            status=JobStatus.PENDING,
            file_hash=data["file_hash"],
            s3_bucket=data["s3_bucket"],
            s3_key=data["s3_key"],
            file_size_bytes=data["file_size_bytes"],
            content_type=data["content_type"],
            row_count_raw=0,
            row_count_clean=0,
            created_at=datetime.now(timezone.utc),
            completed_at=None,
            expires_at=data["expires_at"],
            error_message=None,
        )
        self.jobs[job.id] = job
        return job

    async def get(self, job_id: UUID) -> JobRecord | None:
        return self.jobs.get(job_id)

    async def list(self, *, offset: int, limit: int) -> list[JobRecord]:
        jobs = list(self.jobs.values())
        return jobs[offset : offset + limit]

    async def update(self, job_id: UUID, **changes) -> JobRecord | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        for key, value in changes.items():
            setattr(job, key, value)
        return job

    async def delete(self, job_id: UUID) -> bool:
        return self.jobs.pop(job_id, None) is not None


@pytest.fixture
def client():
    repository = InMemoryJobRepository()
    app.dependency_overrides[get_job_service] = lambda: JobService(repository)
    yield TestClient(app)
    app.dependency_overrides.clear()


def job_payload() -> dict[str, object]:
    return {
        "filename": "expenses.csv",
        "business_label": "Acme Ltd",
        "file_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "s3_bucket": "ledgerguard-local",
        "s3_key": "audits/example/expenses.csv",
        "file_size_bytes": 2048,
        "content_type": "text/csv",
        "expires_at": "2026-10-22T00:00:00Z",
    }


def test_create_audit_returns_pending_job(client):
    # Verifies valid job metadata is validated, persisted by the service, and returned as a 201 response.
    response = client.post("/v1/audits", json=job_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "expenses.csv"
    assert body["status"] == "pending"
    assert "s3_bucket" not in body


def test_get_status_and_list_audits(client):
    # Verifies the created job can be retrieved through the status endpoint and included in the collection endpoint.
    created = client.post("/v1/audits", json=job_payload()).json()

    status_response = client.get(f"/v1/audits/{created['id']}/status")
    list_response = client.get("/v1/audits?offset=0&limit=10")

    assert status_response.status_code == 200
    assert status_response.json()["id"] == created["id"]
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == created["id"]


def test_delete_audit_removes_job(client):
    # Verifies deleting an existing job returns 204 and subsequent status lookup returns the standard 404 response.
    created = client.post("/v1/audits", json=job_payload()).json()

    delete_response = client.delete(f"/v1/audits/{created['id']}")
    status_response = client.get(f"/v1/audits/{created['id']}/status")

    assert delete_response.status_code == 204
    assert status_response.status_code == 404
    assert status_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_create_audit_rejects_invalid_file_hash(client):
    # Verifies the request DTO rejects a non-hexadecimal file hash before application or persistence logic runs.
    payload = job_payload()
    payload["file_hash"] = "not-a-sha256-digest"

    response = client.post("/v1/audits", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_job_service_marks_processing_and_completion():
    # Verifies the job lifecycle transitions from pending to processing to completed with result counts.
    repository = InMemoryJobRepository()
    service = JobService(repository)
    created = await repository.create(**job_payload())

    assert created.status == JobStatus.PENDING

    await service.mark_processing(created.id)
    live_processing = await repository.get(created.id)
    assert live_processing is not None
    assert live_processing.status == JobStatus.PROCESSING

    completed = await service.complete_processing(
        created.id,
        row_count_raw=120,
        row_count_clean=104,
    )

    assert completed.status == JobStatus.COMPLETED
    assert completed.row_count_raw == 120
    assert completed.row_count_clean == 104
    assert completed.completed_at is not None
