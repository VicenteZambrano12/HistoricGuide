"""Select and retain Docker images only within the requested application package."""

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys


DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
IMAGE_BASE = re.compile(r"[a-z0-9-]+-docker\.pkg\.dev/[a-z0-9-]+/[a-z0-9._-]+/[a-z0-9._-]+")


@dataclass(frozen=True)
class Image:
    digest: str
    tags: tuple[str, ...]
    created: datetime


def parse_images(records: object, image_base: str) -> list[Image]:
    if not isinstance(records, list):
        raise ValueError("Artifact Registry must return an image list.")
    images: list[Image] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or record.get("package") != image_base:
            raise ValueError("Artifact Registry returned an image outside the application package.")
        digest = record.get("version")
        tags = record.get("tags", [])
        created = record.get("createTime")
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest) or digest in seen:
            raise ValueError("Artifact Registry returned an invalid or duplicate digest.")
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("Artifact Registry returned invalid image tags.")
        if not isinstance(created, str):
            raise ValueError("Artifact Registry returned no image creation time.")
        timestamp = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("Image creation times must include a timezone.")
        images.append(Image(digest, tuple(tags), timestamp))
        seen.add(digest)
    return sorted(images, key=lambda image: (image.created, image.digest), reverse=True)


def run_gcloud(arguments: list[str]) -> str:
    return subprocess.run(
        ["gcloud", *arguments, "--quiet"], check=True, capture_output=True, text=True,
    ).stdout


def list_images(image_base: str) -> list[Image]:
    output = run_gcloud([
        "artifacts", "docker", "images", "list", image_base, "--include-tags", "--format=json",
    ])
    return parse_images(json.loads(output), image_base)


def select_image(images: list[Image], image_base: str, sha: str, source_changed: bool) -> tuple[str, bool]:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("The image tag must be a full Git commit SHA.")
    matches = [image for image in images if sha in image.tags] if source_changed else images[:1]
    if source_changed and len(matches) > 1:
        raise ValueError("The commit tag resolved to more than one image.")
    if matches:
        return f"{image_base}@{matches[0].digest}", False
    return f"{image_base}:{sha}", True


def prune_targets(images: list[Image], keep_digest: str) -> list[Image]:
    if not DIGEST.fullmatch(keep_digest):
        raise ValueError("Retention requires a valid published image digest.")
    if keep_digest not in {image.digest for image in images[:2]}:
        raise ValueError("The selected image is not among the newest two; no images will be deleted.")
    return images[2:]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select")
    select.add_argument("--image-base", required=True)
    select.add_argument("--sha", required=True)
    select.add_argument("--source-changed", choices=("true", "false"), required=True)
    prune = commands.add_parser("prune")
    prune.add_argument("--image-base", required=True)
    prune.add_argument("--keep-digest", required=True)
    arguments = parser.parse_args()
    if not IMAGE_BASE.fullmatch(arguments.image_base):
        raise ValueError("Expected one explicit regional Artifact Registry application image path.")
    images = list_images(arguments.image_base)
    if arguments.command == "select":
        image, build = select_image(
            images, arguments.image_base, arguments.sha, arguments.source_changed == "true",
        )
        output = os.environ.get("GITHUB_OUTPUT")
        if not output:
            raise ValueError("GITHUB_OUTPUT must be set when selecting the workflow image.")
        with Path(output).open("a", encoding="utf-8") as file:
            file.write(f"image={image}\nbuild={str(build).lower()}\nimage_base={arguments.image_base}\n")
        print(f"Selected {'new build' if build else 'existing digest'}: {image}")
    else:
        targets = prune_targets(images, arguments.keep_digest)
        expected = {image.digest for image in images[:2]}
        for image in targets:
            run_gcloud([
                "artifacts", "docker", "images", "delete",
                f"{arguments.image_base}@{image.digest}", "--delete-tags",
            ])
        remaining = list_images(arguments.image_base)
        if {image.digest for image in remaining} != expected:
            raise ValueError("Artifact Registry did not retain exactly the expected newest images.")
        print(f"Retained {len(remaining)} application images (maximum two), including the selected digest.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stderr or str(error), file=sys.stderr)
        raise SystemExit(error.returncode) from error
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1) from error
