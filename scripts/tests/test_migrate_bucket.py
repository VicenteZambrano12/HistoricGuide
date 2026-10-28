import base64
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import google_crc32c
from google.api_core.exceptions import PreconditionFailed

from scripts.migrate_bucket import build_uploads, main, migrate


class BucketMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.docs = root / "docs"
        self.prompts = root / "prompts"
        document = self.docs / "Pantheon/historic/example.pdf"
        document.parent.mkdir(parents=True)
        document.write_bytes(b"%PDF-1.4\nexample")
        self.prompts.mkdir()
        (self.prompts / "historic.yaml").write_text("system: Example\n", encoding="utf-8")
        self.uploads = build_uploads(self.docs, self.prompts)
        self.client = Mock()
        self.bucket = self.client.get_bucket.return_value
        self.bucket.get_blob.return_value = None

    def test_prefixes_contents_and_checksums(self) -> None:
        self.assertEqual(
            [upload.name for upload in self.uploads],
            ["docs/Pantheon/historic/example.pdf", "prompts/historic.yaml"],
        )
        self.assertEqual(self.uploads[0].content_type, "application/pdf")
        self.assertEqual(self.uploads[1].content_type, "application/yaml")
        for upload in self.uploads:
            self.assertEqual(
                upload.crc32c,
                base64.b64encode(google_crc32c.Checksum(upload.content).digest()).decode("ascii"),
            )

    def test_upload_and_verify(self) -> None:
        blobs = []
        for upload in self.uploads:
            blobs.append(Mock(
                crc32c=upload.crc32c, size=len(upload.content), content_type=upload.content_type,
            ))
        self.bucket.blob.side_effect = blobs
        self.assertEqual(migrate(self.client, "historic-guide", self.uploads), 2)
        self.client.get_bucket.assert_called_once_with("historic-guide")
        for blob, upload in zip(blobs, self.uploads):
            kwargs = blob.upload_from_file.call_args.kwargs
            self.assertEqual(kwargs["if_generation_match"], 0)
            self.assertEqual(kwargs["checksum"], "crc32c")
            self.assertEqual(blob.upload_from_file.call_args.args[0].getvalue(), upload.content)
            blob.reload.assert_called_once()

    def test_unchanged_objects_are_skipped(self) -> None:
        self.bucket.get_blob.side_effect = [
            Mock(crc32c=upload.crc32c, size=len(upload.content), content_type=upload.content_type)
            for upload in self.uploads
        ]
        self.assertEqual(migrate(self.client, "historic-guide", self.uploads), 2)
        self.bucket.blob.assert_not_called()

    def test_update_uses_generation_guard(self) -> None:
        upload = self.uploads[0]
        self.bucket.get_blob.return_value = Mock(crc32c="old", generation=123)
        self.bucket.blob.return_value = Mock(
            crc32c=upload.crc32c, size=len(upload.content), content_type=upload.content_type,
        )
        migrate(self.client, "historic-guide", [upload])
        self.assertEqual(
            self.bucket.blob.return_value.upload_from_file.call_args.kwargs["if_generation_match"], 123,
        )

    def test_concurrent_update_and_verification_errors_propagate(self) -> None:
        blob = self.bucket.blob.return_value
        blob.upload_from_file.side_effect = PreconditionFailed("changed concurrently")
        with self.assertRaises(PreconditionFailed):
            migrate(self.client, "historic-guide", self.uploads)
        blob.upload_from_file.side_effect = None
        blob.crc32c = "wrong"
        with self.assertRaisesRegex(RuntimeError, "verification failed"):
            migrate(self.client, "historic-guide", self.uploads)

    def test_invalid_sources_and_duplicate_plan(self) -> None:
        (self.docs / "ignored.json").write_text("not uploaded")
        self.assertEqual(len(build_uploads(self.docs, self.prompts)), 2)
        with self.assertRaises(ValueError):
            migrate(self.client, "historic-guide", [self.uploads[0], self.uploads[0]])
        self.client.get_bucket.assert_not_called()
        (self.prompts / "historic.yaml").write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "empty"):
            build_uploads(self.docs, self.prompts)
        (self.prompts / "historic.yaml").unlink()
        with self.assertRaisesRegex(ValueError, "No supported files"):
            build_uploads(self.docs, self.prompts)
        with self.assertRaises(ValueError):
            build_uploads(self.docs / "missing", self.prompts)

    def test_symlinks_are_rejected(self) -> None:
        (self.prompts / "linked.yaml").symlink_to(self.prompts / "historic.yaml")
        with self.assertRaisesRegex(ValueError, "Symlinks"):
            build_uploads(self.docs, self.prompts)

    def test_dry_run_never_creates_cloud_client(self) -> None:
        with patch("sys.argv", [
            "migrate_bucket.py", "--dry-run",
            "--docs-dir", str(self.docs), "--prompts-dir", str(self.prompts),
        ]), patch("scripts.migrate_bucket.storage.Client") as client:
            main()
            client.assert_not_called()
            client.from_service_account_json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
