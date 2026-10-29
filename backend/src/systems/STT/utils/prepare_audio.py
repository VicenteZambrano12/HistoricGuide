from pathlib import Path


def prepare_audio(
    audio: str | Path | bytes, *, mime_type: str | None = None
) -> tuple[bytes, str]:
    """Read audio content and resolve its MIME type without transcoding.

    Args:
        audio (str | Path | bytes): Audio file path or in-memory audio bytes.
        mime_type (str | None): Explicit MIME type, or None to infer from a known
            file extension; defaults to None.

    Returns:
        tuple[bytes, str]: Audio bytes and the resolved MIME type.

    Raises:
        TypeError: Audio is neither a file path nor bytes.
        ValueError: No MIME type is supplied for bytes or an unknown extension.
        OSError: The audio file cannot be read.
    """
    if isinstance(audio, (str, Path)):
        path = Path(audio)
        if mime_type is None:
            mime_type = {
                ".wav": "audio/wav",
                ".mp3": "audio/mp3",
                ".aiff": "audio/aiff",
                ".aif": "audio/aiff",
                ".aac": "audio/aac",
                ".ogg": "audio/ogg",
                ".flac": "audio/flac",
                ".webm": "audio/webm",
                ".m4a": "audio/mp4",
                ".mp4": "audio/mp4",
            }.get(path.suffix.lower())
        audio = path.read_bytes()
    if not isinstance(audio, bytes):
        raise TypeError("audio must be a file path or bytes.")
    if mime_type is None:
        raise ValueError("Provide mime_type for audio bytes or unknown file extensions.")
    return audio, mime_type
