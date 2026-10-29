"""Text-to-speech using the Gemini Developer API."""

from dataclasses import dataclass, field

from .utils.create_client import create_client
from .utils.synthesize import synthesize
from src.utils.general.GeminiApiCall import GeminiClient


@dataclass
class TTS:
    """Expose WAV speech synthesis through an injectable Gemini client.

    Args:
        client (GeminiClient): Provider client; defaults to create_client().

    Returns:
        TTS: Configured speech-synthesis service.

    Raises:
        ValueError: Default client credentials or shared configuration are invalid.
        OSError: Shared configuration cannot be read.
    """

    client: GeminiClient = field(default_factory=create_client)

    def synthesize(self, text: str, *, voice: str = "Kore") -> bytes:
        """Synthesize nonblank text as playable mono, 16-bit WAV audio.

        Args:
            text (str): Nonblank text to speak.
            voice (str): Nonblank provider voice identifier; defaults to "Kore".

        Returns:
            bytes: Complete WAV file containing synthesized speech.

        Raises:
            TypeError: Text or voice is not a string.
            ValueError: Text or voice is blank.
            RuntimeError: Provider audio is incomplete, inconsistent, or unsupported.
            OSError: The provider connection fails or times out.
            json.JSONDecodeError: The provider response is not valid JSON.
        """
        return synthesize(self.client, text, voice=voice)
