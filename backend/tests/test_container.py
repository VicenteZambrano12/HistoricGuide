import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.container import create_app


class ContainerTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.frontend = Path(directory.name)
        (self.frontend / "index.html").write_text("<html>HistoricGuide</html>")
        assets = self.frontend / "assets"
        assets.mkdir()
        (assets / "app.js").write_text("console.log('HistoricGuide');")
        self.client = TestClient(create_app(self.frontend))
        self.addCleanup(self.client.close)

    def test_frontend_and_assets_are_served(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertEqual(response.text, "<html>HistoricGuide</html>")
        asset = self.client.get("/assets/app.js")
        self.assertEqual(asset.status_code, 200)
        self.assertEqual(asset.text, "console.log('HistoricGuide');")

    def test_api_health_and_docs_are_available_under_api(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("x-request-id", response.headers)
        docs = self.client.get("/api/docs")
        self.assertEqual(docs.status_code, 200)
        self.assertIn("/api/openapi.json", docs.text)
        schema = self.client.get("/api/openapi.json")
        self.assertEqual(schema.status_code, 200)
        self.assertIn("/chat", schema.json()["paths"])

    @patch("src.api.Endpoint.chat.Pipeline")
    def test_frontend_chat_request_reaches_existing_pipeline(self, pipeline) -> None:
        pipeline.return_value.run.return_value = "An answer."
        response = self.client.post("/api/chat", data={
            "mode": "text", "language": "EN", "stop": "Pantheon", "query": "Explain the dome.",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"text": "An answer."})
        pipeline.return_value.run.assert_called_once_with(
            "Explain the dome.", "only text", stop="Pantheon", mime_type=None,
            language="en", request_type=None,
        )

    @patch.dict(os.environ, ENV="GCP")
    @patch("src.api.Endpoint.documents.bucket_bytes", return_value=b"%PDF-1.4\nexample")
    def test_frontend_pdf_url_preserves_cloud_and_range_behavior(self, download) -> None:
        response = self.client.get(
            "/api/documents/Pantheon/historic/guide.pdf", headers={"Range": "bytes=0-7"},
        )
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, b"%PDF-1.4")
        download.assert_called_once_with("docs/Pantheon/historic/guide.pdf")

    def test_missing_api_and_static_paths_do_not_return_frontend_html(self) -> None:
        response = self.client.get("/api/missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not Found"})
        for path in ("/assets/missing.js", "/.env", "/backend/pyproject.toml"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_missing_frontend_build_fails_startup(self) -> None:
        with self.assertRaises(RuntimeError):
            create_app(self.frontend / "missing")


if __name__ == "__main__":
    unittest.main()
