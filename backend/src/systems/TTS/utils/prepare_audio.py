from io import BytesIO
import wave


def prepare_audio(audio: bytes, *, mime_type: str) -> bytes:
    """Wrap Gemini's little-endian, mono PCM output in a WAV container."""
    media_type, *parameters = mime_type.split(";")
    options = {}
    for parameter in parameters:
        name, separator, value = parameter.strip().partition("=")
        if not separator:
            raise RuntimeError("Gemini returned invalid PCM audio parameters.")
        options[name.lower()] = value.strip()
    if (
        media_type.strip().lower() != "audio/l16"
        or options.get("codec", "pcm") != "pcm"
        or options.get("channels", "1") != "1"
    ):
        raise RuntimeError(f"Unsupported Gemini audio format: {mime_type}.")
    try:
        sample_rate = int(options.get("rate", ""))
    except ValueError as error:
        raise RuntimeError("Gemini returned an invalid PCM sample rate.") from error
    if sample_rate <= 0 or sample_rate > 384_000:
        raise RuntimeError("Gemini returned an invalid PCM sample rate.")
    if not audio or len(audio) % 2:
        raise RuntimeError("Gemini returned empty or incomplete 16-bit PCM audio.")
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(audio)
    return output.getvalue()
