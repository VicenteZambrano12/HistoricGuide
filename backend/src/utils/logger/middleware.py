"""ASGI request logging, including the complete lifetime of streamed responses."""

import logging
from time import perf_counter
from uuid import UUID, uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .logger import Logger, correlation_id


logger = Logger(__name__)


class RequestLoggingMiddleware:
    """Track HTTP request lifetimes without buffering streaming response bodies.

    Args:
        app (ASGIApp): Downstream ASGI application.

    Returns:
        RequestLoggingMiddleware: Correlation-aware request logging middleware.

    Raises:
        None.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Retain the ASGI application to invoke for each connection.

        Args:
            app (ASGIApp): Downstream application callable.

        Returns:
            None: The middleware is initialized in place.

        Raises:
            None.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bind correlation context and log an HTTP request's terminal outcome.

        Args:
            scope (Scope): ASGI connection metadata and request-local state.
            receive (Receive): Callable receiving ASGI request messages.
            send (Send): Callable forwarding ASGI response messages.

        Returns:
            None: Response messages are forwarded without buffering.

        Raises:
            Exception: Downstream application or transport errors are logged and re-raised.
            BaseException: Cancellation or shutdown interrupts processing after cleanup.
        """
        # Mounted apps share request state; only the outer active layer owns access logs.
        if scope["type"] != "http" or scope.get("state", {}).get("_request_logging_active"):
            await self.app(scope, receive, send)
            return

        # Only bounded UUID headers may supply a correlation ID; arbitrary input is replaced.
        supplied_id = Headers(scope=scope).get("x-request-id", "")
        try:
            identifier = str(UUID(supplied_id)) if len(supplied_id) == 36 else str(uuid4())
        except ValueError:
            identifier = str(uuid4())
        state = scope.setdefault("state", {})
        state["request_id"] = state["correlation_id"] = identifier
        state["_request_logging_active"] = True
        token = correlation_id.set(identifier)
        started = perf_counter()
        status_code = 500
        completed = False
        response_started = False

        async def send_response(message: Message) -> None:
            """Record response progress and attach the ID before forwarding headers.

            Args:
                message (Message): Response-start or response-body ASGI message.

            Returns:
                None: The original message is forwarded with correlation headers.

            Raises:
                Exception: The downstream transport rejects the message.
            """
            nonlocal status_code, completed, response_started
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_started = True
                MutableHeaders(scope=message)["X-Request-ID"] = identifier
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                completed = True

        def metadata(event: str) -> dict[str, object]:
            """Build operational metadata without query strings, headers, or bodies.

            Args:
                event (str): Stable identifier for the request lifecycle event.

            Returns:
                dict[str, object]: Connection metadata, current status, and elapsed milliseconds.

            Raises:
                None: Valid HTTP ASGI scopes contain the required method and path.
            """
            route = scope.get("route")
            return {
                "event": event,
                "method": scope["method"],
                "path": scope["path"],
                "route": getattr(route, "path", "<unmatched>"),
                "client_ip": scope["client"][0] if scope.get("client") else None,
                "status_code": status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
            }

        try:
            incoming = metadata("request.started")
            incoming.pop("status_code")
            incoming.pop("duration_ms")
            logger.info("HTTP request received", extra=incoming)
            await self.app(scope, receive, send_response)
        except Exception:
            # The global exception handler owns the traceback; this is the access event.
            logger.error("HTTP request failed", extra=metadata("request.failed"))
            raise
        except BaseException:
            if not response_started:
                status_code = 499
            logger.warning("HTTP request interrupted", extra=metadata("request.interrupted"))
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
            correlation_id.reset(token)
            state.pop("_request_logging_active", None)
