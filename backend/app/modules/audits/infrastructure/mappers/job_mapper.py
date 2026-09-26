from app.schemas.models import Job

from ...domain.entities import JobRecord


def to_domain(job: Job) -> JobRecord:
    return JobRecord(
        id=job.id,
        filename=job.filename,
        business_label=job.business_label,
        status=job.status,
        file_hash=job.file_hash,
        s3_bucket=job.s3_bucket,
        s3_key=job.s3_key,
        file_size_bytes=job.file_size_bytes,
        content_type=job.content_type,
        row_count_raw=job.row_count_raw,
        row_count_clean=job.row_count_clean,
        created_at=job.created_at,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
        error_message=job.error_message,
    )
