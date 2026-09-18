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
os.environ.setdefault("CELERY_BROKER_URL", "redis://redis:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
os.environ.setdefault("LOG_LEVEL", "INFO")
