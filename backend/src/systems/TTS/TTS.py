"""Text-to-speech using the Gemini Developer API."""

from dataclasses import dataclass, field

from .utils.create_client import create_client
from .utils.synthesize import synthesize
from src.utils.general.GeminiApiCall import GeminiClient


@dataclass
class TTS:
    client: GeminiClient = field(default_factory=create_client)

    def synthesize(self, text: str, *, voice: str = "Kore") -> bytes:
        """Synthesize text as mono, 16-bit WAV audio."""
        return synthesize(self.client, text, voice=voice)
