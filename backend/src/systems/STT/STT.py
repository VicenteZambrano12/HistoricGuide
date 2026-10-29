"""Speech-to-text using the Gemini Developer API."""

from dataclasses import dataclass, field
from pathlib import Path

from .utils.create_client import create_client
from .utils.transcribe import transcribe
from src.utils.general.GeminiApiCall import GeminiClient


@dataclass
class STT:
    """Expose original-language transcription through an injectable Gemini client.

    Args:
        client (GeminiClient): Provider client; defaults to create_client().

    Returns:
        STT: Configured transcription service.

    Raises:
        ValueError: Default client credentials or shared configuration are invalid.
        OSError: Shared configuration cannot be read.
    """

    client: GeminiClient = field(default_factory=create_client)

    def transcribe(
        self, audio: str | Path | bytes, *, mime_type: str | None = None
    ) -> str:
        """Transcribe an audio file or bytes without translation or summarization.

        Args:
            audio (str | Path | bytes): Audio file path or in-memory content.
            mime_type (str | None): Optional audio MIME type; required for bytes or
                unrecognized file extensions.

        Returns:
            str: Original-language transcript with surrounding whitespace removed.

        Raises:
            TypeError: Audio is neither a path nor bytes.
            ValueError: Audio content or MIME settings are missing or invalid.
            RuntimeError: Gemini returns no usable or complete transcription.
            OSError: The file or provider connection cannot be accessed.
            json.JSONDecodeError: The provider response is not valid JSON.
        """
        return transcribe(self.client, audio, mime_type=mime_type)