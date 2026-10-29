import asyncio
from io import StringIO
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from starlette.background import BackgroundTask

from src.app import app, server_error
from src.container import create_app
from src.utils.general.progress import report_progress
from src.utils.logger import Logger, correlation_id
from src.utils.logger.Logger import request_id
from src.utils.logger.middleware import RequestLoggingMiddleware


class LoggerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace = logging.getLogger("historicguide")
        self.old_handlers = self.namespace.handlers[:]
        self.old_level = self.namespace.level
        self.old_propagate = self.namespace.propagate
        self.namespace.handlers = []
        self.output = StringIO()
        self.logger = Logger("tests")
        self.configure()

    def tearDown(self) -> None:
        for handler in self.namespace.handlers:
            handler.close()
        self.namespace.handlers = self.old_handlers
        self.namespace.setLevel(self.old_level)
        self.namespace.propagate = self.old_propagate

    def configure(self, *, level: str = "DEBUG", output_format: str = "json") -> None:
        with patch("sys.stdout", self.output):
            Logger.configure(level=level, output_format=output_format)

    def records(self) -> list[dict]:
        return [json.loads(line) for line in self.output.getvalue().splitlines()]

    def test_json_fields_and_lazy_interpolation(self) -> None:
        self.logger.info(
            "Completed %s", "operation",
            extra={"event": "test.completed", "duration_ms": 12.5, "secret": "not-serialized"},
        )
        record, = self.records()
        self.assertEqual(record["message"], "Completed operation")
        self.assertEqual(record["severity"], "INFO")
        self.assertEqual(record["level"], "INFO")
        self.assertEqual(record["logger"], "historicguide.tests")
        self.assertEqual(record["module"], "test_logger")
        self.assertEqual(record["event"], "test.completed")
        self.assertEqual(record["duration_ms"], 12.5)
        self.assertTrue(record["timestamp"].endswith("+00:00"))
        self.assertNotIn("not-serialized", self.output.getvalue())

    def test_configuration_is_idempotent_and_does_not_change_root(self) -> None:
        root = logging.getLogger()
        root_handlers = root.handlers[:]
        root_level = root.level
        self.configure()
        self.configure()
        self.logger.info("Once")
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(len(self.namespace.handlers), 1)
        self.assertEqual(root.handlers, root_handlers)
        self.assertEqual(root.level, root_level)

    def test_levels_and_text_format(self) -> None:
        self.configure(level="WARNING", output_format="text")
        self.logger.info("Hidden")
        self.logger.warning("Line one\nLine two", extra={"event": "test.warning"})
        output = self.output.getvalue()
        self.assertNotIn("Hidden", output)
        self.assertIn("WARNING", output)
        self.assertIn("test.warning", output)
        self.assertEqual(len(output.splitlines()), 1)

    def test_environment_configuration(self) -> None:
        with patch.dict("os.environ", {"LOG_LEVEL": "error", "LOG_FORMAT": "text"}):
            with patch("sys.stdout", self.output):
                Logger.configure()
        self.logger.warning("Hidden")
        self.logger.error("Visible")
        self.assertNotIn("Hidden", self.output.getvalue())
        self.assertIn("ERROR", self.output.getvalue())

    def test_dotenv_configuration_uses_shared_settings(self) -> None:
        with TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text("LOG_LEVEL=ERROR\nLOG_FORMAT=text\n")
            with patch("src.utils.general.GeminiApiCall.ENV_FILE", dotenv), \
                    patch.dict("os.environ", {}, clear=True), patch("sys.stdout", self.output):
                Logger.configure()
        self.logger.warning("Hidden")
        self.logger.error("Visible")
        self.assertNotIn("Hidden", self.output.getvalue())
        self.assertIn("ERROR", self.output.getvalue())
        self.assertNotIn('"severity"', self.output.getvalue())

    def test_invalid_configuration_fails_without_replacing_handler(self) -> None:
        original_handler, = self.namespace.handlers
        for settings in ({"level": "TRACE"}, {"output_format": "xml"}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                Logger.configure(**settings)
            self.assertEqual(self.namespace.handlers, [original_handler])

    def test_exception_has_stack_without_exception_payload(self) -> None:
        try:
            raise RuntimeError("API_KEY=private-user-payload")
        except RuntimeError:
            self.logger.exception("Operation failed", extra={"event": "test.failed"})
        record, = self.records()
        self.assertEqual(record["exception_type"], "RuntimeError")
        self.assertEqual(record["stack"][-1]["function"],
                         "test_exception_has_stack_without_exception_payload")
        self.assertNotIn("private-user-payload", self.output.getvalue())

    def test_chained_exception_preserves_all_frames_without_payloads(self) -> None:
        def provider() -> None:
            raise ValueError("private-provider-payload")

        try:
            try:
                provider()
            except ValueError as error:
                raise RuntimeError("private-wrapper-payload") from error
        except RuntimeError:
            self.logger.exception("Provider failed")
        record, = self.records()
        cause, = record["exception_chain"]
        self.assertEqual(cause["exception_type"], "ValueError")
        self.assertEqual(cause["stack"][-1]["function"], "provider")
        self.assertNotIn("private-provider-payload", self.output.getvalue())
        self.assertNotIn("private-wrapper-payload", self.output.getvalue())

    def test_request_status_timing_and_privacy(self) -> None:
        correlation_id = str(uuid4())
        with TestClient(app) as client, patch("sys.stdout", self.output):
            # Lifespan also configures logging; restore the test capture afterwards.
            self.configure()
            response = client.get("/health?token=private", headers={"X-Request-ID": correlation_id})
            rejected = client.post("/chat", data={"query": "private-question"})
            missing = client.get("/missing?key=private")
        self.assertEqual(response.headers["X-Request-ID"], correlation_id)
        for response in (rejected, missing):
            UUID(response.headers["X-Request-ID"])
        requests = [r for r in self.records() if r.get("event") == "request.completed"]
        self.assertEqual([r["status_code"] for r in requests], [200, 422, 404])
        self.assertEqual([r["severity"] for r in requests], ["INFO", "WARNING", "WARNING"])
        self.assertEqual([r["route"] for r in requests], ["/health", "/chat", "<unmatched>"])
        self.assertEqual([r["path"] for r in requests], ["/health", "/chat", "/missing"])
        self.assertTrue(all(r["client_ip"] == "testclient" for r in requests))
        self.assertEqual(requests[0]["request_id"], correlation_id)
        self.assertEqual(requests[0]["correlation_id"], correlation_id)
        incoming = [r for r in self.records() if r.get("event") == "request.started"]
        self.assertEqual(len(incoming), 3)
        self.assertEqual(incoming[0]["method"], "GET")
        self.assertEqual(incoming[0]["path"], "/health")
        self.assertNotIn("status_code", incoming[0])
        self.assertNotIn("duration_ms", incoming[0])
        self.assertTrue(all(r["duration_ms"] >= 0 for r in requests))
        self.assertNotIn("private", self.output.getvalue())
        self.assertIsNone(request_id.get())

    def test_invalid_request_id_is_replaced(self) -> None:
        with TestClient(app) as client:
            for value in ("not-a-uuid", "x" * 36, "x" * 1000):
                response = client.get("/health", headers={"X-Request-ID": value})
                self.assertNotEqual(response.headers["X-Request-ID"], value)
                UUID(response.headers["X-Request-ID"])

    def test_failure_returns_sanitized_json_and_correlated_traceback(self) -> None:
        correlation_id = str(uuid4())
        with patch("src.api.Endpoint.chat.Pipeline") as pipeline:
            pipeline.return_value.run.side_effect = RuntimeError("secret-provider-body")
            with TestClient(app, raise_server_exceptions=False) as client:
                self.configure()
                response = client.post(
                    "/chat", headers={"X-Request-ID": correlation_id},
                    data={"query": "private-question", "mode": "text",
                          "language": "EN", "stop": "Pantheon"},
                )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Internal Server Error"})
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.headers["X-Request-ID"], correlation_id)
        failures = [r for r in self.records() if r.get("event") == "request.failed"]
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["request_id"], correlation_id)
        self.assertEqual(failures[0]["status_code"], 500)
        self.assertEqual(failures[0]["severity"], "ERROR")
        exceptions = [r for r in self.records() if r.get("event") == "request.exception"]
        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0]["correlation_id"], correlation_id)
        self.assertEqual(exceptions[0]["exception_type"], "RuntimeError")
        self.assertTrue(exceptions[0]["stack"])
        self.assertIsNone(request_id.get())
        self.assertNotIn("secret-provider-body", self.output.getvalue())
        self.assertNotIn("private-question", self.output.getvalue())

    def test_stream_worker_inherits_correlation_and_logs_failure(self) -> None:
        correlation_id = str(uuid4())

        def fail(*args, **kwargs):
            report_progress("generating")
            raise RuntimeError("secret-provider-body")

        with patch("src.api.Endpoint.chat.Pipeline") as pipeline:
            pipeline.return_value.run.side_effect = fail
            with TestClient(app) as client:
                self.configure()
                response = client.post(
                    "/chat", headers={"X-Request-ID": correlation_id},
                    data={"query": "private-question", "mode": "text", "language": "EN",
                          "stop": "Pantheon", "stream": "true"},
                )
        events = [json.loads(line) for line in response.text.splitlines()]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(events[-1]["type"], "error")
        records = [r for r in self.records() if r.get("event") in (
            "pipeline.stage", "chat.stream.failed", "request.completed",
        )]
        self.assertTrue(any(r["event"] == "pipeline.stage" for r in records))
        self.assertEqual(sum(r["event"] == "chat.stream.failed" for r in records), 1)
        self.assertTrue(all(r["request_id"] == correlation_id for r in records))
        self.assertNotIn("secret-provider-body", self.output.getvalue())
        self.assertIsNone(request_id.get())

    def test_concurrent_requests_have_isolated_context(self) -> None:
        identifiers = [str(uuid4()) for _ in range(8)]

        async def run() -> None:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                responses = await asyncio.gather(*(
                    client.get("/health", headers={"X-Request-ID": identifier})
                    for identifier in identifiers
                ))
            self.assertEqual([r.headers["X-Request-ID"] for r in responses], identifiers)

        asyncio.run(run())
        records = [r for r in self.records() if r.get("event") == "request.completed"]
        self.assertCountEqual([r["request_id"] for r in records], identifiers)
        incoming = [r for r in self.records() if r.get("event") == "request.started"]
        self.assertCountEqual([r["correlation_id"] for r in incoming], identifiers)
        self.logger.info("Outside request")
        self.assertNotIn("request_id", self.records()[-1])
        self.assertNotIn("correlation_id", self.records()[-1])

    def test_sync_endpoint_inherits_request_context(self) -> None:
        identifier = str(uuid4())

        def run(*args, **kwargs):
            self.logger.info("Sync worker", extra={"event": "test.sync"})
            return "Answer."

        with patch("src.api.Endpoint.chat.Pipeline") as pipeline:
            pipeline.return_value.run.side_effect = run
            with TestClient(app) as client:
                self.configure()
                response = client.post(
                    "/chat", headers={"X-Request-ID": identifier},
                    data={"query": "question", "mode": "text",
                          "language": "EN", "stop": "Pantheon"},
                )
        self.assertEqual(response.status_code, 200)
        worker, = [r for r in self.records() if r.get("event") == "test.sync"]
        self.assertEqual(worker["correlation_id"], identifier)
        self.assertIs(correlation_id, request_id)
        self.assertIsNone(correlation_id.get())

    def test_container_logs_frontend_and_mounted_api_once(self) -> None:
        with TemporaryDirectory() as directory:
            frontend = Path(directory)
            (frontend / "index.html").write_text("<html>Guide</html>")
            with TestClient(create_app(frontend)) as client:
                self.configure()
                for path in ("/", "/api/health"):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
                    UUID(response.headers["X-Request-ID"])
        for event in ("request.started", "request.completed"):
            records = [r for r in self.records() if r.get("event") == event]
            self.assertEqual([r["path"] for r in records], ["/", "/api/health"])
        self.assertIsNone(correlation_id.get())

    def test_container_errors_have_one_traceback_and_json_response(self) -> None:
        with TemporaryDirectory() as directory:
            frontend = Path(directory)
            (frontend / "index.html").write_text("<html>Guide</html>")
            with TestClient(create_app(frontend), raise_server_exceptions=False) as client:
                self.configure()
                with patch("src.api.Endpoint.chat.Pipeline", side_effect=RuntimeError("private")):
                    api = client.post("/api/chat", data={
                        "query": "question", "mode": "text",
                        "language": "EN", "stop": "Pantheon",
                    })
                with patch("starlette.staticfiles.StaticFiles.get_response",
                           side_effect=RuntimeError("private")):
                    static = client.get("/")
        for response in (api, static):
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json(), {"detail": "Internal Server Error"})
            UUID(response.headers["X-Request-ID"])
        for event in ("request.started", "request.failed", "request.exception"):
            records = [r for r in self.records() if r.get("event") == event]
            self.assertEqual(len(records), 2)
            self.assertCountEqual(
                [r["correlation_id"] for r in records],
                [api.headers["X-Request-ID"], static.headers["X-Request-ID"]],
            )
        self.assertNotIn("private", self.output.getvalue())
        self.assertIsNone(correlation_id.get())

    def test_stream_timing_includes_final_chunk_and_background_logs(self) -> None:
        application = FastAPI(exception_handlers={Exception: server_error})
        application.add_middleware(RequestLoggingMiddleware)

        async def chunks():
            yield b"first"
            await asyncio.sleep(0.02)
            yield b"last"

        def background() -> None:
            self.logger.info("Background completed", extra={"event": "test.background"})

        @application.get("/stream")
        async def stream():
            return StreamingResponse(chunks(), background=BackgroundTask(background))

        with TestClient(application) as client:
            response = client.get("/stream")
        completed, = [r for r in self.records() if r.get("event") == "request.completed"]
        self.assertEqual(response.content, b"firstlast")
        self.assertGreaterEqual(completed["duration_ms"], 20)
        background_record, = [r for r in self.records() if r.get("event") == "test.background"]
        self.assertEqual(background_record["correlation_id"], response.headers["X-Request-ID"])
        self.assertIsNone(correlation_id.get())

    def test_failure_after_headers_does_not_claim_a_500_response(self) -> None:
        application = FastAPI(exception_handlers={Exception: server_error})
        application.add_middleware(RequestLoggingMiddleware)

        def fail() -> None:
            raise RuntimeError("private-background-payload")

        @application.get("/late-failure")
        def late_failure():
            from fastapi.responses import JSONResponse
            return JSONResponse({"ok": True}, background=BackgroundTask(fail))

        with TestClient(application, raise_server_exceptions=False) as client:
            response = client.get("/late-failure")
        self.assertEqual(response.status_code, 200)
        failed, = [r for r in self.records() if r.get("event") == "request.failed"]
        self.assertEqual(failed["status_code"], 200)
        exception, = [r for r in self.records() if r.get("event") == "request.exception"]
        self.assertEqual(exception["correlation_id"], response.headers["X-Request-ID"])
        self.assertNotIn("private-background-payload", self.output.getvalue())

    def test_missing_client_and_cancellation_reset_context(self) -> None:
        async def cancelled(scope, receive, send):
            raise asyncio.CancelledError

        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            self.fail("A cancelled request must not send a response")

        async def run() -> None:
            scope = {"type": "http", "method": "GET", "path": "/cancelled", "headers": []}
            with self.assertRaises(asyncio.CancelledError):
                await RequestLoggingMiddleware(cancelled)(scope, receive, send)
            self.assertIsNone(correlation_id.get())
            self.assertNotIn("_request_logging_active", scope["state"])

        asyncio.run(run())
        interrupted, = [r for r in self.records() if r.get("event") == "request.interrupted"]
        self.assertIsNone(interrupted["client_ip"])
        self.assertEqual(interrupted["status_code"], 499)
        self.assertEqual(interrupted["severity"], "WARNING")

    def test_application_lifecycle(self) -> None:
        with patch("sys.stdout", self.output):
            with TestClient(app):
                pass
        self.assertEqual(
            [r["event"] for r in self.records()],
            ["application.started", "application.stopped"],
        )


if __name__ == "__main__":
    unittest.main()
