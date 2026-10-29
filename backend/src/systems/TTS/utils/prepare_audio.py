from io import BytesIO
import wave


def prepare_audio(audio: bytes, *, mime_type: str) -> bytes:
    """Wrap validated little-endian, mono PCM samples in a WAV container.

    Args:
        audio (bytes): Nonempty complete 16-bit PCM samples from Gemini.
        mime_type (str): audio/l16 MIME type declaring a positive sample rate up to
            384000 Hz; codec and channel parameters must indicate mono PCM.

    Returns:
        bytes: Self-contained WAV file containing the supplied audio samples.

    Raises:
        RuntimeError: MIME parameters, sample rate, or PCM sample boundaries are invalid.
    """
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
    # A trailing partial sample would produce a corrupt 16-bit waveform.
    if not audio or len(audio) % 2:
        raise RuntimeError("Gemini returned empty or incomplete 16-bit PCM audio.")
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(audio)
    return output.getvalue()
