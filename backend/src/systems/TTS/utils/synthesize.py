from src.utils.general.GeminiApiCall import GeminiClient

from .prepare_audio import prepare_audio


def synthesize(client: GeminiClient, text: str, *, voice: str = "Kore") -> bytes:
    """Generate speech with the supplied client and return playable WAV bytes."""
    audio, mime_type = client.generate_audio(text, voice=voice)
    return prepare_audio(audio, mime_type=mime_type)
