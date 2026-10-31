import os
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import warnings
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from google.api_core.exceptions import Forbidden, NotFound
from qdrant_client import QdrantClient, models

from src.app import app
from src.utils.AgentSystem.Orchestrator.load_prompt import load_prompt as orchestrator_prompt
from src.utils.AgentSystem.ResponseGenerator.load_prompt import load_prompt as generation_prompt
from src.utils.AgentSystem.ResponseGenerator.retrieve_chunks import retrieve_chunks
from src.utils.AgentSystem.ResponseGenerator.retrieve_qdrant import qdrant_client
from src.utils.general.cloud import bucket_bytes, environment
from src.utils.general.GeminiApiCall import GeminiClient
from src.utils.general.sources import collecting_sources


class CloudConfigurationTests(unittest.TestCase):
    def test_qdrant_host_uses_http_with_or_without_authentication(self) -> None:
        for key in ("", "test-key"):
            with (
                self.subTest(authenticated=bool(key)),
                patch(
                    "src.utils.AgentSystem.ResponseGenerator.retrieve_qdrant._configuration_value",
                    side_effect=lambda name, default="": {
                        "QDRANT_HOST": "127.0.0.1", "QDRANT_PORT": "6333",
                        "QDRANT_API_KEY": key,
                    }.get(name, default),
                ),
                patch(
                    "src.utils.AgentSystem.ResponseGenerator.retrieve_qdrant.QdrantClient",
                    side_effect=partial(QdrantClient, check_compatibility=False),
                ),
            ):
                with warnings.catch_warnings(record=True):
                    remote = qdrant_client(timeout=3)
                try:
                    self.assertEqual(remote._client.rest_uri, "http://127.0.0.1:6333")
                finally:
                    remote.close()

    def test_qdrant_explicit_url_preserves_protocol_and_overrides_host(self) -> None:
        with (
            patch(
                "src.utils.AgentSystem.ResponseGenerator.retrieve_qdrant._configuration_value",
                side_effect=lambda name, default="": {
                    "QDRANT_URL": "https://qdrant.example:6333",
                    "QDRANT_HOST": "ignored.example", "QDRANT_PORT": "1234",
                    "QDRANT_API_KEY": "test-key",
                }.get(name, default),
            ),
            patch(
                "src.utils.AgentSystem.ResponseGenerator.retrieve_qdrant.QdrantClient",
                side_effect=partial(QdrantClient, check_compatibility=False),
            ),
        ):
            remote = qdrant_client(timeout=3)
            try:
                self.assertEqual(remote._client.rest_uri, "https://qdrant.example:6333")
            finally:
                remote.close()

    def test_explicit_environment_selection_and_invalid_mode(self) -> None:
        for value in ("LOCAL", "GCP"):
            with patch.dict(os.environ, ENV=value):
                self.assertEqual(environment(), value)
        with patch.dict(os.environ, ENV="invalid"), self.assertRaisesRegex(ValueError, "ENV"):
            environment()
        with patch("src.utils.general.cloud._configuration_value", side_effect=lambda name, default="": default):
            self.assertEqual(environment(), "LOCAL")

    def test_adc_and_bucket_download_close_client(self) -> None:
        with patch.dict(os.environ, {
            "GOOGLE_APPLICATION_CREDENTIALS": "", "GCS_BUCKET": "historic-guide",
            "GOOGLE_CLOUD_PROJECT": "basicrahgapp",
        }), patch("src.utils.general.cloud.storage.Client") as factory:
            client = factory.return_value
            client.bucket.return_value.blob.return_value.download_as_bytes.return_value = b"data"
            self.assertEqual(bucket_bytes("prompts/historic.yaml"), b"data")
            client.bucket.assert_called_once_with("historic-guide")
            client.bucket.return_value.blob.assert_called_once_with("prompts/historic.yaml")
            factory.from_service_account_json.assert_not_called()
            client.close.assert_called_once()

    def test_explicit_credentials_resolve_from_repository_root_and_errors_propagate(self) -> None:
        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "config/example.json"}), patch(
            "src.utils.general.cloud.storage.Client",
        ) as factory:
            client = factory.from_service_account_json.return_value
            client.bucket.return_value.blob.return_value.download_as_bytes.side_effect = Forbidden("denied")
            with self.assertRaises(Forbidden):
                bucket_bytes("docs/example.pdf")
            credential_path = factory.from_service_account_json.call_args.args[0]
            self.assertTrue(Path(credential_path).is_absolute())
            self.assertTrue(credential_path.endswith("/config/example.json"))
            client.close.assert_called_once()

    def test_all_prompts_load_from_bucket_with_existing_validation(self) -> None:
        prompts = Path(__file__).resolve().parents[1] / "src/config/prompts"
        with patch.dict(os.environ, ENV="GCP"), patch(
            "src.utils.general.cloud.bucket_bytes",
            side_effect=lambda name: (prompts / name.removeprefix("prompts/")).read_bytes(),
        ) as download:
            self.assertTrue(orchestrator_prompt().system_prompt)
            for category in ("historic", "restaurant"):
                self.assertTrue(generation_prompt(category).system_prompt)
            self.assertEqual([call.args[0] for call in download.call_args_list], [
                "prompts/orchestrator.yaml", "prompts/historic.yaml", "prompts/restaurant.yaml",
            ])

    def test_local_prompts_do_not_access_cloud(self) -> None:
        with patch.dict(os.environ, ENV="LOCAL"), patch("src.utils.general.cloud.bucket_bytes") as download:
            orchestrator_prompt()
            generation_prompt("historic")
            generation_prompt("restaurant")
            download.assert_not_called()


class CloudDocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        mode = patch.dict(os.environ, ENV="GCP")
        mode.start()
        self.addCleanup(mode.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    @patch("src.api.Endpoint.documents.bucket_bytes", return_value=b"%PDF-1.4\nexample")
    def test_cloud_pdf_has_same_inline_range_behavior_and_cleans_up(self, download: Mock) -> None:
        with TemporaryDirectory() as directory, patch("tempfile.tempdir", directory):
            url = "/documents/Pantheon/historic/a%20guide.pdf"
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"%PDF-1.4\nexample")
            self.assertTrue(response.headers["content-disposition"].startswith("inline;"))
            self.assertEqual(response.headers["content-type"], "application/pdf")
            self.assertEqual(list(Path(directory).iterdir()), [])
            partial = self.client.get(url, headers={"Range": "bytes=0-7"})
            self.assertEqual(partial.status_code, 206)
            self.assertEqual(partial.content, b"%PDF-1.4")
            self.assertEqual(list(Path(directory).iterdir()), [])
        download.assert_called_with("docs/Pantheon/historic/a guide.pdf")

    @patch("src.api.Endpoint.documents.bucket_bytes")
    def test_invalid_paths_fail_before_cloud_access(self, download: Mock) -> None:
        for source in ("private.txt", "%2e%2e%2foutside.pdf", "%2Foutside.pdf", "a%5Cb.pdf"):
            with self.subTest(source=source):
                self.assertEqual(self.client.get(f"/documents/{source}").status_code, 404)
        download.assert_not_called()

    @patch("src.api.Endpoint.documents.bucket_bytes", side_effect=NotFound("missing"))
    def test_missing_object_is_404(self, download: Mock) -> None:
        self.assertEqual(self.client.get("/documents/missing.pdf").status_code, 404)

    @patch("src.api.Endpoint.documents.bucket_bytes", side_effect=Forbidden("denied"))
    def test_permission_error_does_not_fall_back_to_local(self, download: Mock) -> None:
        with self.assertRaises(Forbidden):
            self.client.get("/documents/missing.pdf")


class CloudRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        mode = patch.dict(os.environ, {"ENV": "GCP", "QDRANT_COLLECTION": "historic_guide"})
        mode.start()
        self.addCleanup(mode.stop)
        self.remote = QdrantClient(":memory:")
        self.addCleanup(self.remote.close)
        factory = patch(
            "src.utils.AgentSystem.ResponseGenerator.retrieve_qdrant.qdrant_client",
            return_value=self.remote,
        )
        factory.start()
        self.addCleanup(factory.stop)
        close = patch.object(self.remote, "close")
        self.close = close.start()
        self.addCleanup(close.stop)
        self.remote.create_collection(
            "historic_guide", vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE),
        )
        self.client = GeminiClient(api_key="test-key", embedding_model="test-embedding")
        embedding = patch.object(self.client, "embed", return_value=[[1.0, 0.0]])
        self.embed = embedding.start()
        self.addCleanup(embedding.stop)

    def add(self, identifier, vector, *, stop="Pantheon", category="historic", model="test-embedding"):
        self.remote.upsert("historic_guide", [models.PointStruct(
            id=identifier, vector=vector, payload={
                "stop_id": stop, "type": category, "embedding_model": model,
                "embedding_dimensions": 2, "text": f"Text {identifier}",
                "source": f"{stop}/{category}/guide.pdf", "page": identifier,
            },
        )])

    def retrieve(self, category="historic", query="Explain the dome."):
        return retrieve_chunks(self.client, "Pantheon", category, user_query=query)

    def test_cosine_top_two_filters_and_citations(self) -> None:
        self.add(1, [1.0, 0.0])
        self.add(2, [10.0, 1.0])
        self.add(3, [0.0, 1.0])
        self.add(4, [1.0, 0.0], stop="Roman_Forum")
        self.add(5, [1.0, 0.0], category="restaurants")
        with collecting_sources() as sources:
            self.assertEqual(self.retrieve(), ["Text 1", "Text 2"])
        self.assertEqual([source.page for source in sources], [1, 2])
        self.assertEqual(sources[0].source, "Pantheon/historic/guide.pdf")
        self.embed.assert_called_once_with(
            ["Stop: Pantheon\nType: historic\n\nExplain the dome."],
            task_type="RETRIEVAL_QUERY",
        )
        self.close.assert_called_once()

    def test_restaurant_mapping_and_intro(self) -> None:
        self.add(1, [1.0, 0.0], category="restaurants")
        self.assertEqual(self.retrieve(category="restaurant", query=None), ["Text 1"])
        self.assertIn("Type: restaurants", self.embed.call_args.args[0][0])
        self.assertIn("dining options", self.embed.call_args.args[0][0])

    def test_missing_or_model_mismatch_fail_before_embedding(self) -> None:
        with self.assertRaisesRegex(ValueError, "No RAG chunks"):
            self.retrieve()
        self.add(1, [1.0, 0.0], model="wrong-model")
        with self.assertRaisesRegex(RuntimeError, "model mismatch"):
            self.retrieve()
        self.embed.assert_not_called()

    def test_bad_query_vectors_are_rejected(self) -> None:
        self.add(1, [1.0, 0.0])
        for vectors in ([], [[0.0, 0.0]], [[1.0]], [[float("nan"), 1.0]]):
            with self.subTest(vectors=vectors):
                self.embed.return_value = vectors
                with self.assertRaises(RuntimeError):
                    self.retrieve()

    def test_connection_error_does_not_use_sqlite(self) -> None:
        with patch.object(self.remote, "get_collection", side_effect=ConnectionError("offline")):
            with self.assertRaisesRegex(ConnectionError, "offline"):
                self.retrieve()
        self.close.assert_called_once()
        self.embed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
