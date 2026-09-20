"""Unit tests for structured logging and secret redaction."""

import json
import logging

from src.observability.logging import RedactingJsonFormatter


def test_secret_redaction_in_log_formatter():
    formatter = RedactingJsonFormatter(
        "%(timestamp)s %(level)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
    )

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg=(
            "Attempting connection with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 "
            "and sk-1234567890abcdef1234567890"
        ),
        args=(),
        exc_info=None,
    )

    formatted_output = formatter.format(record)
    parsed = json.loads(formatted_output)

    assert "[REDACTED_SECRET]" in parsed["message"]
    assert "eyJhbGci" not in parsed["message"]
    assert "sk-1234567890" not in parsed["message"]
