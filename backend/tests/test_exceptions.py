import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

os.environ.setdefault("POSTGRES_USER", "txn_user")
os.environ.setdefault("POSTGRES_PASSWORD", "txn_password")
os.environ.setdefault("POSTGRES_DB", "txn_pipeline")
os.environ.setdefault("CELERY_BROKER_URL", "redis://redis:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.main import create_app


class ItemPayload(BaseModel):
    name: str
    quantity: int


@pytest.fixture
def client():
    app = create_app()

    @app.get("/test/app-exception")
    async def raise_app_exception():
        raise BadRequestError("Bad payload")

    @app.get("/test/not-found")
    async def raise_not_found():
        raise NotFoundError()

    @app.get("/test/conflict")
    async def raise_conflict():
        raise ConflictError("duplicate")

    @app.get("/test/unauthorized")
    async def raise_unauthorized():
        raise UnauthorizedError("missing token")

    @app.get("/test/forbidden")
    async def raise_forbidden():
        raise ForbiddenError("access denied")

    @app.get("/test/http-exception")
    async def raise_http_exception():
        raise HTTPException(status_code=418, detail="teapot")

    @app.get("/test/unexpected")
    async def raise_unexpected():
        raise RuntimeError("explosive failure")

    @app.get("/test/service-unavailable")
    async def raise_service_unavailable():
        raise ServiceUnavailableError("downstream offline")

    @app.post("/test/validation")
    async def validation(payload: ItemPayload):
        return payload.model_dump()

    return TestClient(app)


def test_app_exception_returns_consistent_error_payload(client):
    response = client.get("/test/app-exception")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "BAD_REQUEST",
            "message": "Bad payload",
            "details": None,
        }
    }


def test_not_found_error_is_mapped_to_http_404(client):
    response = client.get("/test/not-found")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert body["error"]["message"] == "The requested resource was not found."


def test_conflict_error_is_mapped_to_http_409(client):
    response = client.get("/test/conflict")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESOURCE_CONFLICT"


def test_unauthorized_error_is_mapped_to_http_401(client):
    response = client.get("/test/unauthorized")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_forbidden_error_is_mapped_to_http_403(client):
    response = client.get("/test/forbidden")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_http_exception_is_normalized(client):
    response = client.get("/test/http-exception")

    assert response.status_code == 418
    body = response.json()
    assert body["error"]["code"] == "HTTP_ERROR"
    assert body["error"]["message"] == "teapot"


def test_validation_errors_return_structured_details(client):
    response = client.post("/test/validation", json={"quantity": "not-an-int"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Request validation failed."
    assert body["error"]["details"]["fields"]


def test_unexpected_exception_returns_safe_generic_response(client):
    response = client.get("/test/unexpected")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert body["error"]["details"] is None


def test_service_unavailable_is_mapped_to_http_503(client):
    response = client.get("/test/service-unavailable")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
