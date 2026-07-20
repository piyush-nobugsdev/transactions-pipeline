from fastapi import FastAPI

from app.celery_app import celery_app
from app.tasks import ping

app = FastAPI(title="Transaction Pipeline API")


@app.get("/health")
async def health():
    return {"status": "ok"}


# --- Temporary debug endpoints -------------------------------------------
# These exist only to prove the Celery/Redis wiring works before the real
# upload endpoint exists. We'll delete these once /jobs/upload is built.

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
