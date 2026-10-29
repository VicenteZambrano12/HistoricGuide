"""Run the agent pipeline with optional speech input and output."""

from dataclasses import dataclass, field
from pathlib import Path

from src.systems.AgentSystem.AgentPipeline.AgentPipeline import AgentPipeline
from src.systems.STT.STT import STT
from src.systems.TTS.TTS import TTS
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language
from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.Pipeline.dataclasses.types import PipelineMode
from src.utils.Pipeline.run import run


@dataclass
class Pipeline:
    """Compose the text agents with lazily initialized speech services.

    Args:
        agent_pipeline (AgentPipeline): Routing/generation service; defaults to a new instance.
        stt (STT | None): Optional injected transcription service; defaults to None.
        tts (TTS | None): Optional injected synthesis service; defaults to None.

    Returns:
        Pipeline: Reusable end-to-end tour-guide pipeline.

    Raises:
        None: Speech services and provider configuration are resolved when used.
    """

    agent_pipeline: AgentPipeline = field(default_factory=AgentPipeline)
    stt: STT | None = None
    tts: TTS | None = None

    def run(
        self,
        data: str | Path | bytes,
        mode: PipelineMode,
        *,
        stop: str,
        mime_type: str | None = None,
        voice: str = "Kore",
        context: list[str] | None = None,
        language: Language = "en",
        request_type: Category | None = None,
    ) -> str | bytes:
        """Generate an answer with optional speech input and output.

        Args:
            data (str | Path | bytes): Question text, audio file path, or audio bytes.
            mode (Literal["STT", "TTS", "full", "only text"]): Processing mode.
            stop (str): Nonblank tour stop used for routing and retrieval.
            mime_type (str | None): Optional audio MIME type; required for audio bytes.
            voice (str): Speech voice identifier; defaults to "Kore".
            context (list[str] | None): Optional nonblank supporting context.
            language (Literal["en", "es"]): Answer language; defaults to "en".
            request_type (Literal["historic", "restaurant"] | None): Explicit topic;
                defaults to None for classification.

        Returns:
            str | bytes: Answer text for STT/only text, or WAV audio for TTS/full.

        Raises:
            pydantic.ValidationError: Inputs violate field or mode-specific constraints.
            TypeError: Transcription does not produce text.
            ValueError: Service settings or available retrieval data are invalid.
            RuntimeError: Retrieval, generation, or audio conversion fails validation.
            OSError: A required file or provider connection cannot be accessed.
            sqlite3.Error: Local retrieval fails.
            yaml.YAMLError: Prompt configuration cannot be parsed.
            google.api_core.exceptions.GoogleAPIError: A cloud dependency fails.
        """
        return run(
            self,
            data,
            mode,
            stop=stop,
            mime_type=mime_type,
            voice=voice,
            context=context,
            language=language,
            request_type=request_type,
        )