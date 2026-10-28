from pathlib import Path


def prepare_audio(
    audio: str | Path | bytes, *, mime_type: str | None = None
) -> tuple[bytes, str]:
    """Read audio files and resolve the MIME type for transcription."""
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
