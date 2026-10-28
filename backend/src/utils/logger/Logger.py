"""Application logging without changing root or third-party logging handlers."""

from contextvars import ContextVar
from collections.abc import MutableMapping
from datetime import datetime, timezone
import json
import logging
import os
import sys
from threading import RLock
import traceback
from typing import Any


request_id: ContextVar[str | None] = ContextVar("log_request_id", default=None)
_configuration_lock = RLock()
_FIELDS = ("event", "method", "route", "status_code", "duration_ms", "stage", "mode", "language")


class _Formatter(logging.Formatter):
    def __init__(self, output_format: str) -> None:
        super().__init__()
        self.output_format = output_format

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = request_id.get()
        if correlation_id is not None:
            payload["request_id"] = correlation_id
        for field in _FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info is not None and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
            # Provider exceptions can contain URLs, credentials, or request bodies.
            payload["stack"] = [
                {"file": frame.filename, "line": frame.lineno, "function": frame.name}
                for frame in traceback.extract_tb(record.exc_info[2])
            ]
        if self.output_format == "json":
            return json.dumps(payload, ensure_ascii=True)
        metadata = {key: value for key, value in payload.items()
                    if key not in ("timestamp", "severity", "logger", "message")}
        return (
            f"{payload['timestamp']} {record.levelname} {record.name} "
            f"{json.dumps(record.getMessage())} {json.dumps(metadata)}"
        )


class Logger(logging.LoggerAdapter):
    """Named stdlib-compatible logger; pass safe metadata through ``extra``."""

    def __init__(self, name: str) -> None:
        super().__init__(logging.getLogger(f"historicguide.{name}"), {})

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any],
    ) -> tuple[Any, MutableMapping[str, Any]]:
        # Preserve per-call structured fields on Python 3.10+ LoggerAdapter.
        return msg, kwargs

    @classmethod
    def configure(cls, *, level: str | None = None, output_format: str | None = None) -> None:
        """Configure one application handler, failing explicitly on invalid settings."""
        selected_level = (level if level is not None else os.getenv("LOG_LEVEL", "INFO")).upper()
        selected_format = (
            output_format if output_format is not None else os.getenv("LOG_FORMAT", "json")
        ).lower()
        if selected_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL.")
        if selected_format not in ("json", "text"):
            raise ValueError("LOG_FORMAT must be json or text.")
        with _configuration_lock:
            application_logger = logging.getLogger("historicguide")
            for handler in application_logger.handlers[:]:
                application_logger.removeHandler(handler)
                handler.close()
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(_Formatter(selected_format))
            application_logger.addHandler(handler)
            application_logger.setLevel(selected_level)
            application_logger.propagate = False