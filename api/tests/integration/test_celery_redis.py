import time
import httpx

BASE_URL = "http://localhost:8000"


def test_ping_task():
    response = httpx.post(f"{BASE_URL}/debug/ping")

    assert response.status_code == 200

    task_id = response.json()["task_id"]

    for _ in range(20):
        result = httpx.get(f"{BASE_URL}/debug/ping/{task_id}")

        data = result.json()

        if data["status"] == "SUCCESS":
            break

        time.sleep(0.5)

    assert data["status"] == "SUCCESS"
    assert data["result"] == "pong"