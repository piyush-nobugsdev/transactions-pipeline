import time

from app.core.infrastructure.celery_app import celery_app


@celery_app.task(name="app.core.infrastructure.tasks.ping")
def ping() -> str:
    """Dummy task: sleeps 1s then returns 'pong'."""
    time.sleep(1)
    return "pong"
