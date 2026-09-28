from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class JobRecord:
    id: UUID
    filename: str
    business_label: str | None
    status: JobStatus
    file_hash: str
    s3_bucket: str
    s3_key: str
    file_size_bytes: int
    content_type: str
    row_count_raw: int
    row_count_clean: int
    created_at: datetime
    completed_at: datetime | None
    expires_at: datetime
    error_message: str | None
