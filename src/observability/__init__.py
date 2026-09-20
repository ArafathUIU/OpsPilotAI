"""Observability package providing structured logging, metrics, and tracing."""

from src.observability.logging import get_logger, setup_logging

__all__ = ["get_logger", "setup_logging"]
