# /// script
# requires-python = ">=3.10"
# dependencies = ["google-cloud-storage>=3,<4", "google-crc32c>=1.5,<2"]
# ///
"""Upload the PDF corpus and YAML prompts to an existing Google Cloud bucket."""

import argparse
import base64
from dataclasses import dataclass
from io import BytesIO
import logging
from pathlib import Path
import re

import google_crc32c
from google.cloud import storage
from google.cloud.storage.retry import DEFAULT_RETRY_IF_GENERATION_SPECIFIED


ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Upload:
    name: str
    content: bytes
    content_type: str
    crc32c: str


def build_uploads(docs_dir: Path, prompts_dir: Path) -> list[Upload]:
    """Read only PDFs and YAML prompts; preserve paths relative to their roots."""
    uploads: list[Upload] = []
    for root, prefix, extensions, content_type in (
        (docs_dir, "docs", {".pdf"}, "application/pdf"),
        (prompts_dir, "prompts", {".yaml", ".yml"}, "application/yaml"),
    ):
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f"Source must be a real directory, not a symlink: {root}")
        count = 0
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlinks are not allowed in migration sources: {path}")
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            content = path.read_bytes()
            if not content:
                raise ValueError(f"Cannot upload an empty source file: {path}")
            uploads.append(Upload(
                name=f"{prefix}/{path.relative_to(root).as_posix()}",
                content=content,
                content_type=content_type,
                crc32c=base64.b64encode(google_crc32c.Checksum(content).digest()).decode("ascii"),
            ))
            count += 1
        if not count:
            raise ValueError(f"No supported files found in {root}.")
    return uploads


def migrate(client: storage.Client, bucket_name: str, uploads: list[Upload]) -> int:
    """Use generation guards, skip identical objects, and verify remote checksums."""
    if not uploads or len({upload.name for upload in uploads}) != len(uploads):
        raise ValueError("The upload plan must be nonempty with unique object names.")
    bucket = client.get_bucket(bucket_name)
    for upload in uploads:
        existing = bucket.get_blob(upload.name)
        if (
            existing is not None
            and existing.crc32c == upload.crc32c
            and existing.size == len(upload.content)
            and existing.content_type == upload.content_type
        ):
            LOGGER.info("Unchanged: gs://%s/%s", bucket_name, upload.name)
            continue
        blob = bucket.blob(upload.name)
        if existing is not None:
            LOGGER.info("Updating: gs://%s/%s", bucket_name, upload.name)
        # A concurrent modification must fail rather than overwrite another writer.
        blob.upload_from_file(
            BytesIO(upload.content),
            size=len(upload.content),
            content_type=upload.content_type,
            checksum="crc32c",
            if_generation_match=existing.generation if existing is not None else 0,
            retry=DEFAULT_RETRY_IF_GENERATION_SPECIFIED,
            timeout=60,
        )
        blob.reload(timeout=60)
        if (
            blob.crc32c != upload.crc32c
            or blob.size != len(upload.content)
            or blob.content_type != upload.content_type
        ):
            raise RuntimeError(f"Upload verification failed: gs://{bucket_name}/{upload.name}")
        LOGGER.info("Uploaded and verified: gs://%s/%s", bucket_name, upload.name)
    return len(uploads)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default="historic-guide")
    parser.add_argument("--project", default="basicrahgapp")
    parser.add_argument("--docs-dir", type=Path, default=ROOT / "database/docs")
    parser.add_argument("--prompts-dir", type=Path, default=ROOT / "backend/src/config/prompts")
    parser.add_argument(
        "--credentials", type=Path,
        help="Optional service-account JSON file; otherwise use Application Default Credentials.",
    )
    parser.add_argument("--dry-run", action="store_true", help="List local uploads without cloud access.")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", args.bucket):
        parser.error("--bucket must be a bucket name, not a gs:// URL or display heading.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    uploads = build_uploads(args.docs_dir, args.prompts_dir)
    if args.dry_run:
        for upload in uploads:
            LOGGER.info("Would upload: gs://%s/%s (%d bytes)", args.bucket, upload.name, len(upload.content))
        LOGGER.info("Validated %d files; no cloud requests made.", len(uploads))
        return
    if args.credentials is not None:
        client = storage.Client.from_service_account_json(str(args.credentials), project=args.project)
    else:
        client = storage.Client(project=args.project)
    try:
        count = migrate(client, args.bucket, uploads)
    finally:
        client.close()
    LOGGER.info("Migration complete: %d files verified or unchanged in gs://%s.", count, args.bucket)


if __name__ == "__main__":
    main()