"""Environment selection and private Cloud Storage access."""

from pathlib import Path
from typing import Literal

from google.cloud import storage

from src.utils.general.GeminiApiCall import _configuration_value


ROOT = Path(__file__).resolve().parents[4]


def environment() -> Literal["LOCAL", "GCP"]:
    value = _configuration_value("ENV", "LOCAL").strip()
    if value == "LOCAL":
        return "LOCAL"
    if value == "GCP":
        return "GCP"
    raise ValueError("ENV must be LOCAL or GCP.")


def bucket_bytes(name: str) -> bytes:
    bucket = _configuration_value("GCS_BUCKET", "historic-guide").strip()
    if not bucket:
        raise ValueError("GCS_BUCKET must not be empty.")
    credentials = _configuration_value("GOOGLE_APPLICATION_CREDENTIALS").strip()
    project = _configuration_value("GOOGLE_CLOUD_PROJECT", "basicrahgapp").strip()
    if credentials:
        path = Path(credentials)
        if not path.is_absolute():
            path = ROOT / path
        client = storage.Client.from_service_account_json(str(path), project=project)
    else:
        client = storage.Client(project=project)
    try:
        return client.bucket(bucket).blob(name).download_as_bytes(timeout=60, checksum="auto")
    finally:
        client.close()


def prompt_text(path: Path) -> str:
    if environment() == "GCP":
        return bucket_bytes(f"prompts/{path.name}").decode("utf-8")
    return path.read_text(encoding="utf-8")
