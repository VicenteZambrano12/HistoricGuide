"""Speech-to-text using the Gemini Developer API."""

from dataclasses import dataclass, field
from pathlib import Path

from .utils.create_client import create_client
from .utils.transcribe import transcribe
from src.utils.general.GeminiApiCall import GeminiClient


@dataclass
class STT:
    client: GeminiClient = field(default_factory=create_client)

    def transcribe(
        self, audio: str | Path | bytes, *, mime_type: str | None = None
    ) -> str:
        """Transcribe a file or audio bytes; bytes require an explicit MIME type."""
        return transcribe(self.client, audio, mime_type=mime_type)