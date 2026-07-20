from fastapi import FastAPI

from app.core.infrastructure.celery_app import celery_app
from app.core.infrastructure.tasks import ping

app = FastAPI(title="Transaction Pipeline API (backend)")


@app.get("/health")
async def health():
    return {"status": "ok"}


# Temporary debug endpoints to validate Celery wiring.
@app.post("/debug/ping")
async def debug_ping():
    task = ping.delay()
    return {"task_id": task.id}


@app.get("/debug/ping/{task_id}")
async def debug_ping_result(task_id: str):
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }
