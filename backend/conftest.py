import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

for candidate in (ROOT, REPO_ROOT / "api"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

os.environ.setdefault("POSTGRES_USER", "txn_user")
os.environ.setdefault("POSTGRES_PASSWORD", "txn_password")
os.environ.setdefault("POSTGRES_DB", "txn_pipeline")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://txn_user:txn_password@localhost:5432/txn_pipeline")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-access-key")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret-key")
os.environ.setdefault("S3_BUCKET_NAME", "test-bucket")
os.environ.setdefault("S3_REGION", "us-east-1")
os.environ.setdefault("MAX_UPLOAD_SIZE_BYTES", "10485760")
os.environ.setdefault("CELERY_BROKER_URL", "redis://redis:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
os.environ.setdefault("LOG_LEVEL", "INFO")
