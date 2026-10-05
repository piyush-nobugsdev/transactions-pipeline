

from app.core.config import Settings, main_check, settings


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


def test_main_check_redacts_secrets(monkeypatch, capsys):
    monkeypatch.setenv("POSTGRES_USER", "txn_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "super-secret-password")
    monkeypatch.setenv("POSTGRES_DB", "txn_pipeline")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://txn_user:super-secret-password@localhost:5432/txn_pipeline")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret-value")
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("S3_REGION", "us-east-1")

    exit_code = main_check()
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "super-secret-password" not in captured
    assert "aws-secret-value" not in captured
    assert "***" in captured
