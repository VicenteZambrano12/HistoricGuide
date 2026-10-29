"""Application logging without changing root or third-party logging handlers."""

from contextvars import ContextVar
from collections.abc import MutableMapping
from datetime import datetime, timezone
import json
import logging
import sys
from threading import RLock
import traceback
from typing import Any

from src.utils.general.GeminiApiCall import _configuration_value


correlation_id: ContextVar[str | None] = ContextVar("log_correlation_id", default=None)
request_id = correlation_id
_configuration_lock = RLock()
_FIELDS = (
    "event", "method", "path", "route", "client_ip", "status_code",
    "duration_ms", "stage", "mode", "language",
)


class _Formatter(logging.Formatter):
    """Render allowlisted operational fields with request correlation metadata.

    Args:
        output_format (str): "json" for structured output or "text" for readable output;
            validated by Logger.configure before construction.

    Returns:
        _Formatter: Formatter that omits exception messages, source lines, and locals.

    Raises:
        None.
    """

    def __init__(self, output_format: str) -> None:
        """Store the selected serialization format.

        Args:
            output_format (str): Output format selected by the logger configuration.

        Returns:
            None: The formatter is initialized in place.

        Raises:
            None.
        """
        super().__init__()
        self.output_format = output_format

    def format(self, record: logging.LogRecord) -> str:
        """Serialize one log record without exposing arbitrary extras or error payloads.

        Args:
            record (logging.LogRecord): Event and optional exception information to render.

        Returns:
            str: One JSON or text log entry enriched with the active correlation ID.

        Raises:
            TypeError: Message interpolation fails or allowlisted metadata is not JSON-safe.
            ValueError: Message interpolation or JSON serialization rejects a value.
        """
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "severity": record.levelname,
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }
        identifier = correlation_id.get()
        if identifier is not None:
            payload["correlation_id"] = identifier
            payload["request_id"] = identifier
        # An allowlist prevents incidental extras from leaking application or provider data.
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
            error = record.exc_info[1]
            chain = []
            # Exception graphs can contain cycles; retain each cause's frames at most once.
            seen: set[int] = set()
            while error is not None and id(error) not in seen:
                seen.add(id(error))
                error = error.__cause__ or (
                    error.__context__ if not error.__suppress_context__ else None
                )
                if error is not None and id(error) not in seen:
                    chain.append({
                        "exception_type": type(error).__name__,
                        "stack": [
                            {"file": frame.filename, "line": frame.lineno, "function": frame.name}
                            for frame in traceback.extract_tb(error.__traceback__)
                        ],
                    })
            if chain:
                payload["exception_chain"] = chain
        if self.output_format == "json":
            return json.dumps(payload, ensure_ascii=True)
        metadata = {key: value for key, value in payload.items()
                    if key not in ("timestamp", "severity", "logger", "message")}
        return (
            f"{payload['timestamp']} {record.levelname} {record.name} "
            f"{json.dumps(record.getMessage())} {json.dumps(metadata)}"
        )


class Logger(logging.LoggerAdapter):
    """Provide stdlib-compatible logging within the application's isolated namespace.

    Args:
        name (str): Caller module name, typically __name__.

    Returns:
        Logger: Adapter preserving per-call structured fields supplied through extra.

    Raises:
        None.
    """

    def __init__(self, name: str) -> None:
        """Bind the adapter to a historicguide-prefixed logger.

        Args:
            name (str): Module or component name beneath the application namespace.

        Returns:
            None: The adapter is initialized in place.

        Raises:
            None.
        """
        super().__init__(logging.getLogger(f"historicguide.{name}"), {})

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any],
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """Preserve caller-provided logging arguments instead of replacing their extras.

        Args:
            msg (Any): Message or lazily interpolated format string.
            kwargs (MutableMapping[str, Any]): Stdlib logging keyword arguments.

        Returns:
            tuple[Any, MutableMapping[str, Any]]: The unchanged message and arguments.

        Raises:
            None.
        """
        # Preserve per-call structured fields on Python 3.10+ LoggerAdapter.
        return msg, kwargs

    @classmethod
    def configure(cls, *, level: str | None = None, output_format: str | None = None) -> None:
        """Atomically replace application handlers without modifying third-party logging.

        Args:
            level (str | None): DEBUG, INFO, WARNING, ERROR, or CRITICAL, case-insensitive.
                None resolves LOG_LEVEL through shared configuration, defaulting to INFO.
            output_format (str | None): "json" or "text", case-insensitive. None resolves
                LOG_FORMAT through shared configuration, defaulting to "json".

        Returns:
            None: The application namespace receives one stdout handler.

        Raises:
            ValueError: A logging option or shared JSON configuration is invalid.
            OSError: The shared configuration file cannot be read.
        """
        selected_level = (
            level if level is not None else _configuration_value("LOG_LEVEL", "INFO")
        ).upper()
        selected_format = (
            output_format if output_format is not None else _configuration_value("LOG_FORMAT", "json")
        ).lower()
        if selected_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL.")
        if selected_format not in ("json", "text"):
            raise ValueError("LOG_FORMAT must be json or text.")
        # Validation precedes replacement so invalid settings leave the current handler intact.
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