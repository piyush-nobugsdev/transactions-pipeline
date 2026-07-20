import os

from app.core.config import Settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    s = Settings()
    assert s.CELERY_BROKER_URL.startswith("redis://")
    assert s.CELERY_RESULT_BACKEND.startswith("redis://")
