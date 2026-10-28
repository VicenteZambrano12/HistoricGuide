import copy
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.registry_images import list_images, main, parse_images, prune_targets, select_image


BASE = "europe-southwest1-docker.pkg.dev/basicrahgapp/historicguide-repo/historicguide"
SHA = "a" * 40


def record(number: int, *, tags: list[str] | None = None) -> dict:
    return {
        "package": BASE,
        "version": f"sha256:{number:064x}",
        "tags": [] if tags is None else tags,
        "createTime": f"2026-10-28T20:00:{number:02d}Z",
    }


class RegistryImageTests(unittest.TestCase):
    def test_empty_repository_builds_even_without_source_changes(self) -> None:
        self.assertEqual(select_image([], BASE, SHA, False), (f"{BASE}:{SHA}", True))

    def test_changed_source_builds_when_commit_tag_is_absent(self) -> None:
        images = parse_images([record(1)], BASE)
        self.assertEqual(select_image(images, BASE, SHA, True), (f"{BASE}:{SHA}", True))

    def test_unchanged_source_reuses_newest_digest(self) -> None:
        images = parse_images([record(1, tags=[SHA]), record(2)], BASE)
        self.assertEqual(select_image(images, BASE, SHA, False), (f"{BASE}@sha256:{2:064x}", False))

    def test_rerun_reuses_existing_commit_digest(self) -> None:
        images = parse_images([record(1, tags=[SHA])], BASE)
        self.assertEqual(select_image(images, BASE, SHA, True), (f"{BASE}@sha256:{1:064x}", False))

    def test_invalid_sha_or_duplicate_tag_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            select_image([], BASE, "not-a-sha", True)
        images = parse_images([record(1, tags=[SHA]), record(2, tags=[SHA])], BASE)
        with self.assertRaises(ValueError):
            select_image(images, BASE, SHA, True)

    def test_pruning_keeps_exactly_two_newest_not_three(self) -> None:
        images = parse_images([record(1), record(4), record(2), record(3)], BASE)
        targets = prune_targets(images, f"sha256:{4:064x}")
        self.assertEqual([image.digest for image in targets], [f"sha256:{2:064x}", f"sha256:{1:064x}"])

    def test_one_or_two_images_require_no_deletions(self) -> None:
        for count in (1, 2):
            with self.subTest(count=count):
                images = parse_images([record(number) for number in range(1, count + 1)], BASE)
                self.assertEqual(prune_targets(images, f"sha256:{count:064x}"), [])

    def test_missing_old_or_invalid_selected_digest_prevents_deletions(self) -> None:
        images = parse_images([record(1), record(2), record(3)], BASE)
        for digest in (f"sha256:{1:064x}", f"sha256:{9:064x}", "invalid"):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                prune_targets(images, digest)
        with self.assertRaises(ValueError):
            prune_targets([], f"sha256:{1:064x}")

    def test_foreign_packages_and_invalid_metadata_are_rejected(self) -> None:
        for fields in (
            {"package": BASE + "-other"}, {"version": "bad"}, {"tags": "bad"},
            {"tags": [1]}, {"createTime": None}, {"createTime": "bad"},
            {"createTime": "2026-10-28T20:00:00"},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                parse_images([{**record(1), **fields}], BASE)
        with self.assertRaises(ValueError):
            parse_images([record(1), record(1)], BASE)
        with self.assertRaises(ValueError):
            parse_images({}, BASE)

    @patch("scripts.registry_images.run_gcloud")
    def test_list_reads_one_package_with_tags_and_parses_api_shape(self, run) -> None:
        run.return_value = json.dumps([record(1)])
        self.assertEqual(list_images(BASE)[0].digest, f"sha256:{1:064x}")
        run.assert_called_once_with([
            "artifacts", "docker", "images", "list", BASE, "--include-tags", "--format=json",
        ])

    @patch("scripts.registry_images.run_gcloud")
    def test_api_failure_is_not_treated_as_an_empty_repository(self, run) -> None:
        run.side_effect = subprocess.CalledProcessError(1, ["gcloud"], stderr="Permission denied")
        with self.assertRaises(subprocess.CalledProcessError):
            list_images(BASE)

    @patch("scripts.registry_images.list_images")
    def test_invalid_image_base_is_rejected_before_cloud_calls(self, listing) -> None:
        with patch("sys.argv", [
            "registry_images.py", "select", "--image-base", BASE + "\\ninjected",
            "--sha", SHA, "--source-changed", "true",
        ]), self.assertRaises(ValueError):
            main()
        listing.assert_not_called()

    @patch("scripts.registry_images.list_images", return_value=[])
    def test_select_writes_exact_github_output_fields(self, listing) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with patch.dict(os.environ, GITHUB_OUTPUT=str(output)), patch("sys.argv", [
                "registry_images.py", "select", "--image-base", BASE,
                "--sha", SHA, "--source-changed", "false",
            ]):
                main()
            self.assertEqual(output.read_text(), f"image={BASE}:{SHA}\nbuild=true\nimage_base={BASE}\n")

    @patch("scripts.registry_images.run_gcloud")
    @patch("scripts.registry_images.list_images")
    def test_prune_deletes_old_digests_only_and_verifies_remaining_images(self, listing, run) -> None:
        images = parse_images([record(1), record(2), record(3)], BASE)
        listing.side_effect = [images, images[:2]]
        with patch("sys.argv", [
            "registry_images.py", "prune", "--image-base", BASE,
            "--keep-digest", f"sha256:{3:064x}",
        ]):
            main()
        run.assert_called_once_with([
            "artifacts", "docker", "images", "delete", f"{BASE}@sha256:{1:064x}", "--delete-tags",
        ])
        self.assertEqual(listing.call_count, 2)

    @patch("scripts.registry_images.run_gcloud")
    @patch("scripts.registry_images.list_images")
    def test_failed_retention_verification_is_not_reported_as_success(self, listing, run) -> None:
        images = parse_images([record(1), record(2), record(3)], BASE)
        listing.side_effect = [images, copy.copy(images)]
        with patch("sys.argv", [
            "registry_images.py", "prune", "--image-base", BASE,
            "--keep-digest", f"sha256:{3:064x}",
        ]), self.assertRaisesRegex(ValueError, "exactly"):
            main()


if __name__ == "__main__":
    unittest.main()
