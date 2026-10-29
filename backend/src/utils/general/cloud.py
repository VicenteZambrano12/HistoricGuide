"""Environment selection and private Cloud Storage access."""

from pathlib import Path
from typing import Literal

from google.cloud import storage

from src.utils.general.GeminiApiCall import _configuration_value


ROOT = Path(__file__).resolve().parents[4]


def environment() -> Literal["LOCAL", "GCP"]:
    """Resolve the explicitly supported data-source environment.

    Args:
        None.

    Returns:
        Literal["LOCAL", "GCP"]: Configured environment; defaults to LOCAL.

    Raises:
        ValueError: ENV or the shared JSON configuration is invalid.
        OSError: The local configuration file cannot be read.
    """
    value = _configuration_value("ENV", "LOCAL").strip()
    if value == "LOCAL":
        return "LOCAL"
    if value == "GCP":
        return "GCP"
    raise ValueError("ENV must be LOCAL or GCP.")


def bucket_bytes(name: str) -> bytes:
    """Download a private corpus object and close its storage client.

    Args:
        name (str): Object key within GCS_BUCKET, such as docs/stop/guide.pdf.

    Returns:
        bytes: Downloaded object content with transport checksum verification.

    Raises:
        ValueError: Bucket or shared configuration is invalid.
        OSError: A configured service-account file cannot be read.
        google.auth.exceptions.DefaultCredentialsError: Default credentials are unavailable.
        google.api_core.exceptions.GoogleAPIError: Download, authorization, or lookup fails.
        google.cloud.storage.exceptions.DataCorruption: Download checksum verification fails.
    """
    bucket = _configuration_value("GCS_BUCKET", "historic-guide").strip()
    if not bucket:
        raise ValueError("GCS_BUCKET must not be empty.")
    credentials = _configuration_value("GOOGLE_APPLICATION_CREDENTIALS").strip()
    project = _configuration_value("GOOGLE_CLOUD_PROJECT", "basicrahgapp").strip()
    # Explicit credentials support local development; deployed services use attached identity.
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
    """Load UTF-8 prompt text from the active local or cloud data source.

    Args:
        path (Path): Local prompt path whose basename identifies the cloud prompt object.

    Returns:
        str: Decoded prompt contents.

    Raises:
        ValueError: Environment or storage configuration is invalid.
        OSError: The local prompt or credentials file cannot be read.
        UnicodeDecodeError: Prompt contents are not valid UTF-8.
        google.auth.exceptions.DefaultCredentialsError: Cloud credentials are unavailable.
        google.api_core.exceptions.GoogleAPIError: Cloud prompt retrieval fails.
    """
    if environment() == "GCP":
        return bucket_bytes(f"prompts/{path.name}").decode("utf-8")
    return path.read_text(encoding="utf-8")
