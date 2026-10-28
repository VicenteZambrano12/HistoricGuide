"""ASGI request logging, including the complete lifetime of streamed responses."""

import logging
from time import perf_counter
from uuid import UUID, uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .Logger import Logger, request_id


logger = Logger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        supplied_id = Headers(scope=scope).get("x-request-id", "")
        try:
            correlation_id = str(UUID(supplied_id)) if len(supplied_id) == 36 else str(uuid4())
        except ValueError:
            correlation_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = correlation_id
        token = request_id.set(correlation_id)
        started = perf_counter()
        status_code = 500
        completed = False

        async def send_response(message: Message) -> None:
            nonlocal status_code, completed
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = correlation_id
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                completed = True

        def metadata(event: str) -> dict[str, object]:
            route = scope.get("route")
            return {
                "event": event,
                "method": scope["method"],
                # Never log raw URLs: document paths and query strings can be sensitive.
                "route": getattr(route, "path", "<unmatched>"),
                "status_code": status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
            }

        try:
            await self.app(scope, receive, send_response)
        except Exception:
            logger.exception("HTTP request failed", extra=metadata("request.failed"))
            raise
        else:
            level = (
                logging.ERROR if status_code >= 500 else
                logging.WARNING if status_code >= 400 or not completed else logging.INFO
            )
            logger.log(
                level, "HTTP request completed" if completed else "HTTP request interrupted",
                extra=metadata("request.completed" if completed else "request.interrupted"),
            )
        finally:
            request_id.reset(token)
