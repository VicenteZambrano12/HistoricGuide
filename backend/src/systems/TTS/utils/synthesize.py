from src.utils.general.GeminiApiCall import GeminiClient

from .prepare_audio import prepare_audio


def synthesize(client: GeminiClient, text: str, *, voice: str = "Kore") -> bytes:
    """Generate provider speech and convert its validated PCM output to WAV.

    Args:
        client (GeminiClient): Configured speech-generation client.
        text (str): Nonblank text to speak.
        voice (str): Nonblank provider voice identifier; defaults to "Kore".

    Returns:
        bytes: Playable mono, 16-bit WAV audio.

    Raises:
        TypeError: Text or voice is not a string.
        ValueError: Text or voice is blank.
        RuntimeError: Provider audio or PCM parameters are incomplete or unsupported.
        OSError: The provider connection fails or times out.
        json.JSONDecodeError: The provider response is not valid JSON.
    """
    audio, mime_type = client.generate_audio(text, voice=voice)
    return prepare_audio(audio, mime_type=mime_type)
