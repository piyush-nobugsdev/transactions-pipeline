from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.audits.domain.entities import JobStatus


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    business_label: str | None
    status: JobStatus
    file_hash: str
    file_size_bytes: int
    content_type: str
    created_at: datetime
    completed_at: datetime | None
    expires_at: datetime
    error_message: str | None


class JobListResponse(BaseModel):
    items: list[JobResponse]
    offset: int
    limit: int
