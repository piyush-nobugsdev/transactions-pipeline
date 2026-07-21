from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    loc: list[str | int] = Field(default_factory=list)
    msg: str
    type: str


class ValidationErrorDetail(BaseModel):
    fields: list[ErrorDetail] = Field(default_factory=list)


class ErrorPayload(BaseModel):
    error: dict[str, Any]
