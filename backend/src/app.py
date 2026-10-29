from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.Endpoint.chat import router as chat_router
from src.api.Endpoint.documents import router as documents_router
from src.api.Endpoint.demo import router as demo_router
from src.api.Endpoint.health import router as health_router
from src.utils.logger import Logger, correlation_id
from src.utils.logger.middleware import RequestLoggingMiddleware


logger = Logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Configure application logging and bracket the server lifecycle with events.

    Args:
        application (FastAPI): Application managed by the ASGI lifespan protocol.

    Returns:
        AsyncContextManager[None]: Lifecycle context consumed by FastAPI.

    Yields:
        None: Control while the application accepts requests.

    Raises:
        ValueError: Logging settings or shared JSON configuration are invalid.
        OSError: Shared configuration cannot be read.
    """
    Logger.configure()
    logger.info("Backend started", extra={"event": "application.started"})
    try:
        yield
    finally:
        logger.info("Backend stopped", extra={"event": "application.stopped"})


app = FastAPI(
    lifespan=lifespan,
    title="HistoricGuide API",
    summary="Multilingual historical guidance and speech for Rome tours.",
    version="0.1.0",
    description="""
## Overview

HistoricGuide answers historical and restaurant questions about Rome tour stops.
Submit text or audio to receive a guide's answer in English or Spanish.
Depending on the chat mode, the response is JSON text or a WAV audio file.
The health endpoint provides a lightweight process-liveness check.

## Authentication and configuration

These endpoints are public: **no client authentication or authorization is
currently enforced**, and no authorization header is required. Chat requires
the server's `GEMINI_API_KEY` configuration; clients must never send that key.
No 401 or 403 responses are defined by the current application.

## Requests and standard errors

Chat accepts `multipart/form-data`, not a JSON request body.
HTTP errors use a JSON `detail` string. Request validation failures use either
that string or a `detail` array of objects containing `loc`, `msg`, and `type`;
additional validation context may also be present.

- **400**: a malformed multipart request could not be parsed.
- **404**: an unknown URL returns `{"detail": "Not Found"}`.
- **413**: an uploaded audio file exceeds 14,000,000 bytes.
- **422**: required fields, field values, or mode-specific input are invalid.
- **500**: an unhandled server or upstream failure returns the sanitized JSON
  body `{"detail": "Internal Server Error"}` and an `X-Request-ID` header.

See each operation for its applicable responses and examples.
""",
    contact={
        "name": "HistoricGuide repository",
        "url": "https://github.com/VicenteZambrano12/HistoricGuide",
    },
    license_info={"name": "License not specified"},
    openapi_tags=[
        {
            "name": "health",
            "description": (
                "Process-liveness checks without external service calls. "
                "A successful check does not establish chat readiness."
            ),
        },
        {
            "name": "demo",
            "description": (
                "On-demand shared VM startup and bounded document-collection readiness. "
                "These operations are separate from process liveness."
            ),
        },
        {
            "name": "chat",
            "description": (
                "Tour-stop questions with text or audio input and JSON or WAV "
                "output. All modes execute the guide's agent pipeline."
            ),
        },
    ],
)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(Exception)
async def server_error(request: Request, error: Exception) -> JSONResponse:
    """Log an unhandled exception once and construct a sanitized server response.

    Args:
        request (Request): Failed request carrying correlation and deduplication state.
        error (Exception): Unhandled error whose stack is recorded without its payload.

    Returns:
        JSONResponse: HTTP 500 JSON with a generic detail and, when available,
        the request's X-Request-ID header.

    Raises:
        None.
    """
    # Starlette's error handler can run after user middleware resets its context.
    identifier = getattr(request.state, "correlation_id", None)
    token = correlation_id.set(identifier)
    try:
        # Mounted apps may encounter the same error in more than one server-error layer.
        if getattr(request.state, "_logged_exception", None) is not error:
            request.state._logged_exception = error
            logger.error(
                "Unhandled server exception",
                exc_info=(type(error), error, error.__traceback__),
                extra={"event": "request.exception", "method": request.method,
                       "path": request.url.path},
            )
        return JSONResponse(
            {"detail": "Internal Server Error"}, status_code=500,
            headers={"X-Request-ID": identifier} if identifier is not None else None,
        )
    finally:
        correlation_id.reset(token)


app.include_router(health_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(demo_router)