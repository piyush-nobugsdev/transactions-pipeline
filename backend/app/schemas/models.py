import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


# ============================================================
# Enums
# ============================================================


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TransactionStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


class AnomalyReason(str, enum.Enum):
    STATISTICAL_OUTLIER = "statistical_outlier"
    CURRENCY_MISMATCH = "currency_mismatch"
    DUPLICATE_PAYMENT = "duplicate_payment"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================
# Job
# ============================================================


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    business_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )

    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    s3_bucket: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    s3_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    row_count_raw: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    row_count_clean: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "business_label",
            "file_hash",
            name="uq_job_business_file_hash",
        ),
    )


# ============================================================
# Transaction
# ============================================================


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    txn_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    merchant: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    status: Mapped[TransactionStatus] = mapped_column(
        Enum(
            TransactionStatus,
            name="transaction_status",
        ),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Uncategorised",
    )

    account_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_anomaly: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    anomaly_reason: Mapped[AnomalyReason | None] = mapped_column(
        Enum(
            AnomalyReason,
            name="anomaly_reason",
        ),
        nullable=True,
    )

    duplicate_of_txn_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    llm_category: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    llm_raw_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    llm_failed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )


# ============================================================
# Job Summary
# ============================================================


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    total_spend_inr: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    total_spend_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    top_merchants: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    anomaly_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    duplicate_payment_flagged_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    narrative: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            name="risk_level",
        ),
        nullable=False,
    )




