from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ..entities import JobRecord


class JobRepository(Protocol):
    async def create(
        self,
        *,
        filename: str,
        business_label: str | None,
        file_hash: str,
        s3_bucket: str,
        s3_key: str,
        file_size_bytes: int,
        content_type: str,
        expires_at: datetime,
    ) -> JobRecord: ...

    async def get(self, job_id: UUID) -> JobRecord | None: ...

    async def list(self, *, offset: int, limit: int) -> list[JobRecord]: ...

    async def update(self, job_id: UUID, **changes: object) -> JobRecord | None: ...

    async def delete(self, job_id: UUID) -> bool: ...
