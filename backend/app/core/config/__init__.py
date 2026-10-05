from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

from pydantic import AliasChoices, Field, ValidationError, model_validator
from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = REPO_ROOT / ".env"
SENSITIVE_KEYS = {
    "POSTGRES_PASSWORD",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SECRET_KEY_ID",
    "GEMINI_API_KEY",
    "DATABASE_URL",
}


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

    # Object storage
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AWS_SECRET_ACCESS_KEY", "AWS_SECRET_KEY_ID"),
    )
    AWS_SECRET_KEY_ID: str | None = Field(
        default=None,
        exclude=True,
    )
    S3_BUCKET_NAME: str
    S3_REGION: str
    JOB_RETENTION_DAYS: int = 30
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

    # Celery / Redis
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def aws_secret_key(self) -> str:
        return self.AWS_SECRET_ACCESS_KEY or self.AWS_SECRET_KEY_ID or ""

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        if not self.aws_secret_key:
            raise ValueError("AWS secret key is required. Set AWS_SECRET_ACCESS_KEY or AWS_SECRET_KEY_ID.")
        return self

    model_config = {
        # Load the repo-level .env regardless of the working directory so dev,
        # CI, and pytest all resolve the same configuration source.
        "env_file": str(ENV_FILE),
        "extra": "ignore",
    }

    def redacted_model_dump(self) -> dict[str, Any]:
        data = self.model_dump()
        redacted = dict(data)
        for key in redacted:
            if key in {"POSTGRES_PASSWORD", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SECRET_KEY_ID"}:
                redacted[key] = "***"
            elif key == "DATABASE_URL":
                redacted[key] = re.sub(r"(://)([^:@]+:)([^@]+@)", r"\1\2***@", redacted[key])
        return redacted


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
        print(json.dumps(s.redacted_model_dump(), indent=2))
        return 0
    except ValidationError as exc:
        print("Environment validation failed:\n", exc)
        return 1


if __name__ == "__main__":
    code = main_check()
    sys.exit(code)
