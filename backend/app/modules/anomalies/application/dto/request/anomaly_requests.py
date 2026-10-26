from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ScanAnomaliesRequest(BaseModel):
    job_id: UUID
    outlier_multiplier: Decimal = Field(default=Decimal("3.0"), ge=Decimal("1.0"))
