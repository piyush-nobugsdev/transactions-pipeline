from __future__ import annotations

import asyncio
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import ServiceUnavailableError


class S3Storage:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_key_id: str,
    ) -> None:
        self.bucket = bucket
        self._client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_key_id,
        )

    async def upload(self, *, key: str, content: bytes, content_type: str) -> None:
        await self._run(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    async def download(self, *, key: str) -> bytes:
        response = await self._run(self._client.get_object, Bucket=self.bucket, Key=key)
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, *, key: str) -> None:
        await self._run(self._client.delete_object, Bucket=self.bucket, Key=key)

    async def exists(self, *, key: str) -> bool:
        try:
            await self._run(self._client.head_object, Bucket=self.bucket, Key=key)
            return True
        except ServiceUnavailableError as exc:
            if getattr(exc, "details", None) == {"not_found": True}:
                return False
            raise

    async def _run(self, operation: Any, **kwargs: Any) -> Any:
        try:
            return await asyncio.to_thread(operation, **kwargs)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                raise ServiceUnavailableError(
                    "Storage object was not found.",
                    details={"not_found": True},
                ) from exc
            raise ServiceUnavailableError("Object storage operation failed.") from exc
        except BotoCoreError as exc:
            raise ServiceUnavailableError("Object storage operation failed.") from exc
