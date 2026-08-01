

from app.core.config import Settings, settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://txn_user:txn_password@localhost:5432/txn_pipeline")
    s = Settings()
    assert s.CELERY_BROKER_URL.startswith("redis://")
    assert s.CELERY_RESULT_BACKEND.startswith("redis://")
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")


def test_settings_module_exports_settings():
    assert settings is not None
    assert hasattr(settings, "DATABASE_URL")
