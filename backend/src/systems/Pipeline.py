"""Run the agent pipeline with optional speech input and output."""

from dataclasses import dataclass, field
from pathlib import Path

from src.systems.AgentSystem.AgentPipeline.AgentPipeline import AgentPipeline
from src.systems.STT.STT import STT
from src.systems.TTS.TTS import TTS
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language
from src.utils.Pipeline.dataclasses.types import PipelineMode
from src.utils.Pipeline.run import run


@dataclass
class Pipeline:
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
    ) -> str | bytes:
        """Return answer text or WAV bytes; all modes include the agents."""
        return run(
            self,
            data,
            mode,
            stop=stop,
            mime_type=mime_type,
            voice=voice,
            context=context,
            language=language,
        )