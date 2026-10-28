from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.app import app


class DocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / "docs"
        self.root.mkdir()
        root_patch = patch("src.api.Endpoint.documents.DOCUMENTS_ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def test_pdf_is_served_inline_with_range_support(self) -> None:
        path = self.root / "Pantheon" / "historic" / "a guide.pdf"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"%PDF-1.4\nsource document\n%%EOF")
        url = "/documents/Pantheon/historic/a%20guide.pdf"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.headers["content-disposition"].startswith("inline;"))
        self.assertEqual(response.content, path.read_bytes())
        partial = self.client.get(url, headers={"Range": "bytes=0-7"})
        self.assertEqual(partial.status_code, 206)
        self.assertEqual(partial.content, b"%PDF-1.4")

    def test_missing_non_pdf_and_traversal_paths_are_rejected(self) -> None:
        (self.root / "private.txt").write_text("private")
        outside = self.root.parent / "outside.pdf"
        outside.write_bytes(b"not public")
        (self.root / "escape.pdf").symlink_to(outside)
        for source in (
            "missing.pdf", "private.txt", "%2e%2e%2foutside.pdf",
            "%2Fetc%2Fpasswd", "escape.pdf",
        ):
            with self.subTest(source=source):
                self.assertEqual(self.client.get(f"/documents/{source}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
