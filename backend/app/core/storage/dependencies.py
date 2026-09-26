from fastapi import Depends

from app.core.config import settings

from .s3 import S3Storage


def get_storage() -> S3Storage:
    return S3Storage(
        bucket=settings.S3_BUCKET_NAME,
        region=settings.S3_REGION,
        access_key_id=settings.AWS_ACCESS_KEY_ID,
        secret_key_id=settings.AWS_SECRET_KEY_ID,
    )
