from fastapi import FastAPI, Request

from app.core.exceptions import register_exception_handlers
from app.core.infrastructure.celery_app import celery_app
from app.core.infrastructure.tasks import ping
from app.core.logging import configure_logging, get_logger, set_correlation_context

logger = get_logger(__name__)


def create_app() -> FastAPI:
    configure_logging(force=True)
    app = FastAPI(title="Transaction Pipeline API (backend)")
    register_exception_handlers(app)

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        job_id = request.headers.get("X-Job-ID") or request.query_params.get("job_id")
        with set_correlation_context(job_id=job_id, service="api", component="fastapi"):
            logger.info(
                "request received",
                extra={
                    "event": "request_received",
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            response = await call_next(request)
            logger.info(
                "request completed",
                extra={
                    "event": "request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                },
            )
            return response

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # Temporary debug endpoints to validate Celery wiring.
    @app.post("/debug/ping")
    async def debug_ping(request: Request):
        job_id = request.headers.get("X-Job-ID") or request.query_params.get("job_id")
        task = ping.delay(job_id=job_id)
        return {"task_id": task.id}

    @app.get("/debug/ping/{task_id}")
    async def debug_ping_result(task_id: str):
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
        }

    return app


app = create_app()
