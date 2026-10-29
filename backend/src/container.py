"""Serve the built frontend and the existing API from one Cloud Run container."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.app import app as backend_app, lifespan, server_error
from src.utils.general.GeminiApiCall import _json_configuration
from src.utils.logger.middleware import RequestLoggingMiddleware


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend/dist"


def create_app(frontend_directory: Path = FRONTEND_DIST) -> FastAPI:
    """Build the combined frontend/API application used by the Cloud Run container.

    Args:
        frontend_directory (Path): Built frontend assets; defaults to FRONTEND_DIST.

    Returns:
        FastAPI: Application mounting the backend at /api and static assets at /.

    Raises:
        ValueError: APP_SECRETS_JSON is not a nonempty object of string values.
        RuntimeError: The frontend build directory does not exist.
    """
    _json_configuration()
    application = FastAPI(
        lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None,
    )
    application.add_middleware(RequestLoggingMiddleware)
    application.add_exception_handler(Exception, server_error)
    application.mount("/api", backend_app)
    application.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
    return application
