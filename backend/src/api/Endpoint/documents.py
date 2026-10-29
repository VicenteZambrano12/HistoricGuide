"""Serve only source PDFs contained in the document corpus."""

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from google.api_core.exceptions import NotFound
from starlette.background import BackgroundTask

from src.utils.general.cloud import bucket_bytes, environment


DOCUMENTS_ROOT = Path(__file__).resolve().parents[4] / "database/docs"
router = APIRouter()


@router.get("/documents/{source:path}", summary="Open a source PDF")
def document(source: str) -> FileResponse:
    """Serve a corpus PDF from local storage or a temporary cloud download.

    Args:
        source (str): PDF path relative to the configured document corpus.

    Returns:
        FileResponse: Inline PDF response supporting byte ranges; cloud downloads
        are deleted by a background task after delivery.

    Raises:
        HTTPException: The path is unsafe, is not a PDF, or is missing (404).
        ValueError: Environment or storage configuration is invalid.
        OSError: A local file or temporary download cannot be read or written.
        google.api_core.exceptions.GoogleAPIError: Cloud access fails for a reason
            other than a missing object.
        google.auth.exceptions.DefaultCredentialsError: Cloud credentials are unavailable.
    """
    if environment() == "GCP":
        parts = source.split("/")
        # Validate object names before cloud access; remote keys have no filesystem boundary.
        if (
            not source or any(part in ("", ".", "..") for part in parts)
            or "\\" in source or "\x00" in source
            or Path(source).suffix.lower() != ".pdf"
        ):
            raise HTTPException(404, "Source PDF not found.")
        try:
            content = bucket_bytes(f"docs/{source}")
        except NotFound as error:
            raise HTTPException(404, "Source PDF not found.") from error
        # FileResponse needs a stable path until transmission and range handling finish.
        with NamedTemporaryFile(suffix=".pdf", delete=False) as file:
            path = Path(file.name)
            try:
                file.write(content)
            except BaseException:
                path.unlink(missing_ok=True)
                raise
        return FileResponse(
            path, media_type="application/pdf", filename=parts[-1],
            content_disposition_type="inline",
            background=BackgroundTask(path.unlink, missing_ok=True),
        )
    root = DOCUMENTS_ROOT.resolve()
    # Resolving symlinks before the containment check prevents corpus escapes.
    path = (root / source).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() != ".pdf" or not path.is_file():
        raise HTTPException(404, "Source PDF not found.")
    return FileResponse(
        path, media_type="application/pdf", filename=path.name,
        content_disposition_type="inline",
    )
