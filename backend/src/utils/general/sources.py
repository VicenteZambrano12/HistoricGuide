"""Collect PDF provenance within one chat request without changing pipeline output."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic import BaseModel, Field


class PdfSource(BaseModel):
    """Represent the document and physical PDF page backing a retrieved chunk.

    Args:
        source (str): Nonempty corpus-relative document path.
        page (int): Strictly positive physical page number.

    Returns:
        PdfSource: Validated provenance reference.

    Raises:
        pydantic.ValidationError: The source is empty or the page is not a positive integer.
    """

    # Path safety is enforced by the document endpoint; this field only requires text.
    source: str = Field(min_length=1, description="PDF path relative to database/docs.")
    # Strict integer validation excludes booleans and coercion from strings or floats.
    page: int = Field(gt=0, strict=True, description="One-based PDF page number.")


_sources: ContextVar[list[PdfSource] | None] = ContextVar("pdf_sources", default=None)


def report_sources(sources: list[PdfSource]) -> None:
    """Append unique references to the active request's provenance collector.

    Args:
        sources (list[PdfSource]): Validated references in retrieval order.

    Returns:
        None: The active collector is updated; calls outside a collector have no effect.

    Raises:
        None.
    """
    collected = _sources.get()
    if collected is not None:
        for source in sources:
            if source not in collected:
                collected.append(source)


@contextmanager
def collecting_sources() -> Iterator[list[PdfSource]]:
    """Isolate a mutable provenance list for the duration of a request operation.

    Args:
        None.

    Returns:
        ContextManager[list[PdfSource]]: Context that restores the prior collector on exit.

    Yields:
        list[PdfSource]: Initially empty list populated by report_sources.

    Raises:
        None: Exceptions from the managed operation propagate after context cleanup.
    """
    sources: list[PdfSource] = []
    token = _sources.set(sources)
    try:
        yield sources
    finally:
        _sources.reset(token)
