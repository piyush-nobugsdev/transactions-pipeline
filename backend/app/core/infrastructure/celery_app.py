from celery import Celery

from app.core.config import get_settings


def make_celery():
    settings = get_settings()
    celery = Celery(
        "txn_pipeline",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.core.infrastructure.tasks"],
    )
    return celery


celery_app = make_celery()
celery_app.autodiscover_tasks(["app.core.infrastructure.tasks"])
