from __future__ import annotations

import sys

from typing import Optional

from pydantic import ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Celery / Redis
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        # CI creates `.env` at the repository root. When running the env-check
        # from the `backend` working directory we want to load that file.
        env_file = "../.env"
        extra = "ignore"


_INSTANCE: Optional[Settings] = None


def get_settings() -> Settings:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = Settings()
    return _INSTANCE


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
