from __future__ import annotations

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.core.exceptions import ServiceUnavailableError
from app.core.storage.s3 import S3Storage


@pytest.mark.asyncio
async def test_s3_client_error_logs_aws_diagnostics(caplog):
    storage = S3Storage(
        bucket="audit-bucket",
        region="us-east-1",
        access_key_id="test-access-key",
        secret_key_id="test-secret-key",
    )

    def fail_put_object(**kwargs):
        raise ClientError(
            {
                "Error": {"Code": "AccessDenied", "Message": "Access Denied"},
                "ResponseMetadata": {
                    "HTTPStatusCode": 403,
                    "RequestId": "request-123",
                },
            },
            "PutObject",
        )

    with pytest.raises(ServiceUnavailableError, match="Object storage operation failed"):
        await storage._run(
            fail_put_object,
            Bucket="audit-bucket",
            Key="audits/example.csv",
        )

    record = next(record for record in caplog.records if record.getMessage() == "S3 operation failed")
    assert record.event == "s3_operation_failed"
    assert record.operation == "fail_put_object"
    assert record.bucket == "audit-bucket"
    assert record.aws_error_code == "AccessDenied"
    assert record.aws_error_message == "Access Denied"
    assert record.http_status == 403
    assert record.aws_request_id == "request-123"
    assert not hasattr(record, "secret_key_id")


@pytest.mark.asyncio
async def test_s3_transport_error_logs_exception_type_and_message(caplog):
    storage = S3Storage(
        bucket="audit-bucket",
        region="us-east-1",
        access_key_id="test-access-key",
        secret_key_id="test-secret-key",
    )

    def fail_request(**kwargs):
        raise EndpointConnectionError(endpoint_url="https://s3.us-east-1.amazonaws.com")

    with pytest.raises(ServiceUnavailableError, match="Object storage operation failed"):
        await storage._run(fail_request, Bucket="audit-bucket")

    record = next(record for record in caplog.records if record.getMessage() == "S3 operation failed")
    assert record.exception_type == "EndpointConnectionError"
    assert "s3.us-east-1.amazonaws.com" in record.error_message
