"""Collect PDF provenance within one chat request without changing pipeline output."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic import BaseModel, Field


class PdfSource(BaseModel):
    """A retrieved chunk's document and one-based physical PDF page."""

    source: str = Field(min_length=1, description="PDF path relative to database/docs.")
    page: int = Field(gt=0, strict=True, description="One-based PDF page number.")


_sources: ContextVar[list[PdfSource] | None] = ContextVar("pdf_sources", default=None)


def report_sources(sources: list[PdfSource]) -> None:
    collected = _sources.get()
    if collected is not None:
        for source in sources:
            if source not in collected:
                collected.append(source)


@contextmanager
def collecting_sources() -> Iterator[list[PdfSource]]:
    sources: list[PdfSource] = []
    token = _sources.set(sources)
    try:
        yield sources
    finally:
        _sources.reset(token)
