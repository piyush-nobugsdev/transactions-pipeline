import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ping_task():

    response = client.post("/debug/ping")

    assert response.status_code == 200

    task_id = response.json()["task_id"]

    for _ in range(10):
        result = client.get(f"/debug/ping/{task_id}")

        data = result.json()

        if data["status"] == "SUCCESS":
            break

        time.sleep(0.5)

    assert data["status"] == "SUCCESS"
    assert data["result"] == "pong"