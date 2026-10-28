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
    logger.debug("Pipeline stage", extra={"event": "pipeline.stage", "stage": step})
    reporter = _reporter.get()
    if reporter is not None:
        reporter(step)


@contextmanager
def progress_reporting(reporter: Callable[[ProgressStep], None]) -> Iterator[None]:
    token = _reporter.set(reporter)
    try:
        yield
    finally:
        _reporter.reset(token)
