import asyncio
from io import StringIO
import json
import logging
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.app import app
from src.utils.general.progress import report_progress
from src.utils.logger import Logger
from src.utils.logger.Logger import request_id


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
        self.assertEqual(record["logger"], "historicguide.tests")
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

    def test_request_status_timing_and_privacy(self) -> None:
        correlation_id = str(uuid4())
        with TestClient(app) as client, patch("sys.stdout", self.output):
            # Lifespan also configures logging; restore the test capture afterwards.
            self.configure()
            response = client.get("/health?token=private", headers={"X-Request-ID": correlation_id})
            rejected = client.post("/chat", data={"query": "private-question"})
            missing = client.get("/private-path?key=private")
        self.assertEqual(response.headers["X-Request-ID"], correlation_id)
        for response in (rejected, missing):
            UUID(response.headers["X-Request-ID"])
        requests = [r for r in self.records() if r.get("event") == "request.completed"]
        self.assertEqual([r["status_code"] for r in requests], [200, 422, 404])
        self.assertEqual([r["severity"] for r in requests], ["INFO", "WARNING", "WARNING"])
        self.assertEqual([r["route"] for r in requests], ["/health", "/chat", "<unmatched>"])
        self.assertEqual(requests[0]["request_id"], correlation_id)
        self.assertTrue(all(r["duration_ms"] >= 0 for r in requests))
        self.assertNotIn("private", self.output.getvalue())
        self.assertIsNone(request_id.get())

    def test_invalid_request_id_is_replaced(self) -> None:
        with TestClient(app) as client:
            for value in ("not-a-uuid", "x" * 36, "x" * 1000):
                response = client.get("/health", headers={"X-Request-ID": value})
                self.assertNotEqual(response.headers["X-Request-ID"], value)
                UUID(response.headers["X-Request-ID"])

    def test_failure_retains_500_behavior_and_correlation(self) -> None:
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
        self.assertEqual(response.text, "Internal Server Error")
        self.assertEqual(response.headers["X-Request-ID"], correlation_id)
        failures = [r for r in self.records() if r.get("event") == "request.failed"]
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["request_id"], correlation_id)
        self.assertEqual(failures[0]["status_code"], 500)
        self.assertEqual(failures[0]["severity"], "ERROR")
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
        self.logger.info("Outside request")
        self.assertNotIn("request_id", self.records()[-1])

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
