from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.transactions.domain.entities import AnomalyReason, TransactionStatus


class CreateTransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    txn_id: str | None = Field(default=None, max_length=255)
    date: date
    merchant: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    status: TransactionStatus = TransactionStatus.PENDING
    category: str = Field(default="Uncategorised", min_length=1, max_length=255)
    account_id: str = Field(min_length=1, max_length=255)
    is_anomaly: bool = False
    anomaly_reason: AnomalyReason | None = None
    duplicate_of_txn_id: str | None = Field(default=None, max_length=255)
    llm_category: str | None = Field(default=None, max_length=255)
    llm_raw_response: str | None = None
    llm_failed: bool = False

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("merchant")
    @classmethod
    def normalize_merchant(cls, value: str) -> str:
        return value.strip()
