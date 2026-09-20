"""Structured JSON logging with trace context injection and secret redaction."""

import logging
import re
import sys

try:
    from pythonjsonlogger.json import JsonFormatter
except ImportError:
    from pythonjsonlogger.jsonlogger import JsonFormatter


# Regex pattern to identify and redact sensitive tokens and keys
SECRET_PATTERN = re.compile(
    r"(?i)(bearer\s+[a-zA-Z0-9_\-\.]{15,}|"
    r"sk-[a-zA-Z0-9]{20,}|"
    r"(?:password|secret|api_key|token|access_token|private_key)\s*[:=]\s*['\"][^'\"]+['\"])",
)


class RedactingJsonFormatter(JsonFormatter):
    """Custom JSON formatter that strips secrets and redacts sensitive parameters."""

    def format(self, record: logging.LogRecord) -> str:
        # Redact raw message string if present
        if isinstance(record.msg, str):
            record.msg = SECRET_PATTERN.sub("[REDACTED_SECRET]", record.msg)

        # Redact any extra args if string
        if isinstance(record.args, dict):
            sanitized = {}
            for k, v in record.args.items():
                if isinstance(v, str):
                    sanitized[k] = SECRET_PATTERN.sub("[REDACTED_SECRET]", v)
                else:
                    sanitized[k] = v
            record.args = sanitized

        return super().format(record)


def setup_logging(log_level: str = "INFO") -> None:
    """Configures root logger with structured JSON formatting to stdout."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    formatter = RedactingJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s %(incident_id)s "
        "%(trace_id)s %(agent)s %(duration_ms)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger."""
    return logging.getLogger(name)
