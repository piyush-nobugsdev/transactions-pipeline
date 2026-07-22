import io
import json
import logging

from app.core.logging import (
    configure_logging,
    clear_correlation_context,
    get_correlation_context,
    get_logger,
    log_stage,
    set_correlation_context,
)


def _capture_logs(**kwargs):
    stream = io.StringIO()
    configure_logging(stream=stream, force=True, **kwargs)
    return stream


def test_structured_json_logging_emits_expected_fields():
    stream = _capture_logs(level="DEBUG")
    logger = get_logger("test.logging")

    with set_correlation_context(job_id="job-123", stage="ingest"):
        logger.info("job created", extra={"event": "job_created"})

    payload = json.loads(stream.getvalue().strip())

    assert payload["level"] == "INFO"
    assert payload["event"] == "job_created"
    assert payload["job_id"] == "job-123"
    assert payload["stage"] == "ingest"
    assert payload["message"] == "job created"


def test_context_is_isolated_between_operations():
    stream = _capture_logs(level="INFO")
    logger = get_logger("test.logging")

    with set_correlation_context(job_id="job-1"):
        logger.info("first event", extra={"event": "first_event"})

    logger.info("second event", extra={"event": "second_event"})

    payloads = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]

    assert payloads[0]["job_id"] == "job-1"
    assert "job_id" not in payloads[1]


def test_stage_logging_includes_duration_ms():
    stream = _capture_logs(level="INFO")
    logger = get_logger("test.logging")

    with log_stage(logger, "data_cleaning", event="stage_completed"):
        pass

    payload = json.loads(stream.getvalue().strip())
    assert payload["stage"] == "data_cleaning"
    assert payload["event"] == "stage_completed"
    assert payload["duration_ms"] >= 0


def test_sensitive_values_are_redacted():
    stream = _capture_logs(level="WARNING")
    logger = get_logger("test.logging")

    logger.warning(
        "sensitive payload",
        extra={
            "event": "secret_logged",
            "api_key": "abc123",
            "authorization": "Bearer secret-token",
        },
    )

    payload = json.loads(stream.getvalue().strip())

    assert payload["api_key"] == "<redacted>"
    assert payload["authorization"] == "<redacted>"
