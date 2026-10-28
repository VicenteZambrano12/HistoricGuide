"""Serve the built frontend and the existing API from one Cloud Run container."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.app import app as backend_app, lifespan


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend/dist"


def create_app(frontend_directory: Path = FRONTEND_DIST) -> FastAPI:
    application = FastAPI(
        lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None,
    )
    application.mount("/api", backend_app)
    application.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
    return application
