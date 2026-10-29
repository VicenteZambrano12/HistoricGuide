"""Request-scoped operational progress, without model reasoning or prompt data."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Literal

from src.utils.logger import Logger

logger = Logger(__name__)

ProgressStep = Literal["starting", "transcribing", "routing", "retrieving", "generating", "synthesizing"]
_reporter: ContextVar[Callable[[ProgressStep], None] | None] = ContextVar(
    "progress_reporter", default=None,
)


def report_progress(step: ProgressStep) -> None:
    """Log an operational stage and notify the current request's progress callback.

    Args:
        step (ProgressStep): Safe stage identifier without user or model-generated content.

    Returns:
        None: The event is logged and delivered when a callback is registered.

    Raises:
        Exception: A registered callback fails; its exception propagates unchanged.
    """
    logger.debug("Pipeline stage", extra={"event": "pipeline.stage", "stage": step})
    reporter = _reporter.get()
    if reporter is not None:
        reporter(step)


@contextmanager
def progress_reporting(reporter: Callable[[ProgressStep], None]) -> Iterator[None]:
    """Temporarily bind a progress callback without affecting concurrent requests.

    Args:
        reporter (Callable[[ProgressStep], None]): Callback for operational stage events.

    Returns:
        ContextManager[None]: Context that restores the previous callback on exit.

    Yields:
        None: Control while the supplied callback is active.

    Raises:
        None: Exceptions from the managed operation propagate after context cleanup.
    """
    token = _reporter.set(reporter)
    try:
        yield
    finally:
        _reporter.reset(token)
