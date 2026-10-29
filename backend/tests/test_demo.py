import io
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from fastapi.testclient import TestClient
from qdrant_client import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from src.app import app


class DemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        mode = patch.dict(os.environ, {
            "ENV": "GCP", "QDRANT_COLLECTION": "historic_guide",
            "EMBEDDING_MODEL": "gemini-embedding-001",
        })
        mode.start()
        self.addCleanup(mode.stop)

    def ready_remote(self) -> Mock:
        remote = Mock()
        remote.get_collection.return_value = SimpleNamespace(
            points_count=115, config=SimpleNamespace(params=SimpleNamespace(
                vectors=models.VectorParams(size=768, distance=models.Distance.COSINE),
            )),
        )
        remote.scroll.return_value = ([models.Record(id=1, payload={
            "embedding_model": "gemini-embedding-001", "embedding_dimensions": 768,
        })], None)
        return remote

    @patch("src.api.Endpoint.demo.qdrant_client")
    @patch("src.api.Endpoint.demo.urlopen")
    def test_local_mode_never_wakes_vm_or_contacts_qdrant(self, upstream, remote) -> None:
        with patch.dict(os.environ, ENV="LOCAL"):
            for response in (self.client.post("/demo/start"), self.client.get("/demo/ready")):
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "ready", "reason": None, "retryable": False})
                self.assertEqual(response.headers["cache-control"], "no-store")
        upstream.assert_not_called()
        remote.assert_not_called()

    @patch("src.api.Endpoint.demo.urlopen")
    def test_liveness_remains_side_effect_free(self, upstream) -> None:
        with patch("src.api.Endpoint.demo.qdrant_client") as remote:
            response = self.client.get("/health")
        self.assertEqual(response.json(), {"status": "ok"})
        upstream.assert_not_called()
        remote.assert_not_called()

    @patch("src.api.Endpoint.demo.urlopen")
    def test_starter_running_and_transitional_states_do_not_claim_readiness(self, upstream) -> None:
        for code, state in (
            (200, "already_running"), (202, "starting"), (202, "stopping"),
            (202, "suspending"), (202, "staging"), (202, "provisioning"),
        ):
            with self.subTest(state=state):
                result = io.BytesIO(json.dumps({"status": state}).encode())
                result.status = code
                upstream.return_value.__enter__.return_value = result
                response = self.client.post("/demo/start")
                self.assertEqual(response.status_code, 202)
                self.assertEqual(response.json()["status"], "starting")
                self.assertTrue(response.json()["retryable"])
                request = upstream.call_args.args[0]
                self.assertEqual(request.method, "POST")
                self.assertEqual(request.full_url, "https://start-qdrant-vm-ksvn4nelea-no.a.run.app")
                self.assertEqual(upstream.call_args.kwargs["timeout"], 10)

    @patch("src.api.Endpoint.demo.urlopen")
    def test_concurrent_start_conflicts_and_transient_errors_are_retryable(self, upstream) -> None:
        for code in (409, 429, 500, 502, 503, 504, 403):
            with self.subTest(code=code):
                upstream.side_effect = HTTPError("https://unused", code, "sensitive", {}, None)
                response = self.client.post("/demo/start")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["retryable"], code != 403)
                self.assertNotIn("sensitive", response.text)

    @patch("src.api.Endpoint.demo.urlopen")
    def test_starter_network_errors_are_visible_and_retryable(self, upstream) -> None:
        for error in (URLError("sensitive"), TimeoutError("sensitive")):
            with self.subTest(error=type(error)):
                upstream.side_effect = error
                response = self.client.post("/demo/start")
                self.assertEqual(response.status_code, 503)
                self.assertTrue(response.json()["retryable"])
                self.assertNotIn("sensitive", response.text)

    @patch("src.api.Endpoint.demo.urlopen")
    def test_invalid_starter_responses_fail_explicitly(self, upstream) -> None:
        for data in (b"<html>sensitive</html>", b"[]", b'{"status":"ready"}'):
            with self.subTest(data=data):
                result = io.BytesIO(data)
                result.status = 200
                upstream.return_value.__enter__.return_value = result
                response = self.client.post("/demo/start")
                self.assertEqual(response.status_code, 503)
                self.assertFalse(response.json()["retryable"])
                self.assertNotIn("sensitive", response.text)

    def test_readiness_checks_collection_model_dimensions_and_closes_connections(self) -> None:
        remote = self.ready_remote()
        with (
            patch("src.api.Endpoint.demo.qdrant_client", return_value=remote) as factory,
            patch("src.api.Endpoint.demo.urlopen") as upstream,
        ):
            response = self.client.get("/demo/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
        self.assertEqual(response.headers["cache-control"], "no-store")
        factory.assert_called_once_with(timeout=3)
        remote.get_collection.assert_called_once_with("historic_guide")
        remote.scroll.assert_called_once_with("historic_guide", limit=1, with_payload=True, with_vectors=False)
        remote.close.assert_called_once()
        upstream.assert_not_called()

    def test_missing_empty_and_incompatible_collections_are_not_ready(self) -> None:
        for failure, reason in (
            ("missing", "collection_missing"), ("empty", "collection_empty"),
            ("model", "collection_incompatible"), ("dimensions", "collection_incompatible"),
            ("vectors", "collection_incompatible"),
        ):
            with self.subTest(failure=failure):
                remote = self.ready_remote()
                if failure == "missing":
                    remote.get_collection.side_effect = UnexpectedResponse(
                        status_code=404, reason_phrase="Not Found", content=b"sensitive", headers={},
                    )
                elif failure == "empty":
                    remote.get_collection.return_value.points_count = 0
                elif failure == "vectors":
                    remote.get_collection.return_value.config.params.vectors.distance = models.Distance.DOT
                else:
                    remote.scroll.return_value[0][0].payload[
                        "embedding_model" if failure == "model" else "embedding_dimensions"
                    ] = "wrong" if failure == "model" else 42
                with patch("src.api.Endpoint.demo.qdrant_client", return_value=remote):
                    response = self.client.get("/demo/ready")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["reason"], reason)
                self.assertFalse(response.json()["retryable"])
                self.assertNotIn("sensitive", response.text)
                remote.close.assert_called_once()

    def test_stopped_vm_readiness_is_retryable_and_never_starts_vm(self) -> None:
        remote = self.ready_remote()
        remote.get_collection.side_effect = ResponseHandlingException(TimeoutError("sensitive"))
        with (
            patch("src.api.Endpoint.demo.qdrant_client", return_value=remote),
            patch("src.api.Endpoint.demo.urlopen") as upstream,
        ):
            response = self.client.get("/demo/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "waiting", "reason": "unreachable", "retryable": True})
        self.assertEqual(response.headers["retry-after"], "5")
        self.assertNotIn("sensitive", response.text)
        upstream.assert_not_called()
        remote.close.assert_called_once()

    def test_readiness_configuration_failure_is_explicit(self) -> None:
        with patch.dict(os.environ, QDRANT_COLLECTION=""):
            response = self.client.get("/demo/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["reason"], "configuration")
        self.assertFalse(response.json()["retryable"])

    def test_wakeup_is_post_only(self) -> None:
        with patch("src.api.Endpoint.demo.urlopen") as upstream:
            response = self.client.get("/demo/start")
        self.assertEqual(response.status_code, 405)
        upstream.assert_not_called()
