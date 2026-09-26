from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from pydantic import ValidationError
from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

    # Object storage
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_KEY_ID: str
    S3_BUCKET_NAME: str
    S3_REGION: str
    JOB_RETENTION_DAYS: int = 30
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

    # Celery / Redis
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        # Load the repo-level .env regardless of the working directory so dev,
        # CI, and pytest all resolve the same configuration source.
        env_file = str(ENV_FILE)
        extra = "ignore"


_INSTANCE: Optional[Settings] = None


def get_settings() -> Settings:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = Settings()
    return _INSTANCE


settings = get_settings()


def main_check() -> int:
    try:
        s = Settings()
        print(s.model_dump_json(indent=2))
        return 0
    except ValidationError as exc:
        print("Environment validation failed:\n", exc)
        return 1


if __name__ == "__main__":
    # Minimal CLI: exit non-zero when env invalid
    code = main_check()
    sys.exit(code)
