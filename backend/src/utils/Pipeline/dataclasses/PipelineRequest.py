from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category, NonEmptyText
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language

from .types import PipelineMode


class PipelineRequest(BaseModel):
    """Validate speech/text inputs against the selected end-to-end pipeline mode.

    Args:
        data (str | Path | bytes): Required question text, audio path, or audio bytes.
        mode (Literal["STT", "TTS", "full", "only text"]): Required processing mode.
        stop (str): Required nonblank tour stop.
        language (Literal["en", "es"]): Answer language; defaults to "en".
        request_type (Literal["historic", "restaurant"] | None): Explicit topic;
            defaults to None for automatic classification.
        mime_type (str | None): Audio MIME type; defaults to None and is required
            for bytes in audio-input modes.
        voice (str): Nonblank speech voice; defaults to "Kore".
        context (list[str]): Nonblank supporting texts; defaults to a new empty list.

    Returns:
        PipelineRequest: Strictly validated, mode-compatible pipeline input.

    Raises:
        pydantic.ValidationError: Fields are invalid, extra, or incompatible with the mode.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    # Audio-input modes accept paths or bytes; text-input modes require nonblank strings.
    data: str | Path | bytes
    # The literal mode determines whether transcription and synthesis are executed.
    mode: PipelineMode
    # Stop names are strict strings, stripped of whitespace, with at least one character.
    stop: NonEmptyText
    # English is selected unless the caller explicitly requests Spanish.
    language: Language = "en"
    # None enables classification; explicit values are limited to the supported topics.
    request_type: Category | None = None
    # Nonblank audio MIME values are required for bytes and forbidden for text input.
    mime_type: NonEmptyText | None = None
    # Voice identifiers must be nonblank; the provider validates voice availability.
    voice: NonEmptyText = "Kore"
    # A fresh list prevents context sharing; every supplied item must be nonblank text.
    context: list[NonEmptyText] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_mode_input(self) -> "PipelineRequest":
        """Enforce mode-specific requirements after strict field validation.

        Args:
            None.

        Returns:
            PipelineRequest: The validated request instance.

        Raises:
            ValueError: Audio is empty, its MIME type is missing/invalid, or text-mode
                data and MIME settings are incompatible.
        """
        if self.mode in ("STT", "full"):
            if isinstance(self.data, (str, bytes)) and not self.data:
                raise ValueError("Audio must not be empty.")
            if isinstance(self.data, bytes) and self.mime_type is None:
                raise ValueError("Provide mime_type for audio bytes.")
            if self.mime_type is not None and not self.mime_type.startswith("audio/"):
                raise ValueError("mime_type must be an audio MIME type.")
        else:
            if not isinstance(self.data, str) or not self.data.strip():
                raise ValueError("TTS and only text modes require nonempty text.")
            if self.mime_type is not None:
                raise ValueError("mime_type is only valid for STT and full modes.")
        return self
