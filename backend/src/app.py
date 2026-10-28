from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from src.api.Endpoint.chat import router as chat_router
from src.api.Endpoint.documents import router as documents_router
from src.api.Endpoint.health import router as health_router
from src.utils.logger import Logger
from src.utils.logger.middleware import RequestLoggingMiddleware


logger = Logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
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
- **500**: an unhandled server or upstream failure. With the default non-debug
  configuration, the body is plain text `Internal Server Error`, not JSON.

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
async def server_error(request: Request, error: Exception) -> PlainTextResponse:
    return PlainTextResponse(
        "Internal Server Error", status_code=500,
        headers={"X-Request-ID": request.state.request_id},
    )


app.include_router(health_router)
app.include_router(chat_router)
app.include_router(documents_router)