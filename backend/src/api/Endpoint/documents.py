"""Serve only source PDFs contained in the document corpus."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


DOCUMENTS_ROOT = Path(__file__).resolve().parents[4] / "database/docs"
router = APIRouter()


@router.get("/documents/{source:path}", summary="Open a source PDF")
def document(source: str) -> FileResponse:
    root = DOCUMENTS_ROOT.resolve()
    path = (root / source).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() != ".pdf" or not path.is_file():
        raise HTTPException(404, "Source PDF not found.")
    return FileResponse(
        path, media_type="application/pdf", filename=path.name,
        content_disposition_type="inline",
    )
