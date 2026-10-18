from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category, NonEmptyText
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language

from .types import PipelineMode


class PipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    data: str | Path | bytes
    mode: PipelineMode
    stop: NonEmptyText
    language: Language = "en"
    request_type: Category | None = None
    mime_type: NonEmptyText | None = None
    voice: NonEmptyText = "Kore"
    context: list[NonEmptyText] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_mode_input(self) -> "PipelineRequest":
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
