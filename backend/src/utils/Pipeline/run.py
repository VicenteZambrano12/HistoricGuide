from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from src.systems.STT.STT import STT
from src.systems.TTS.TTS import TTS
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language
from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.general.progress import report_progress
from src.utils.logger import Logger

from .dataclasses.PipelineRequest import PipelineRequest
from .dataclasses.types import PipelineMode

if TYPE_CHECKING:
    from src.systems.Pipeline import Pipeline

logger = Logger(__name__)


def run(
    pipeline: "Pipeline",
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
    """Execute the validated speech/text workflow and record pipeline timing.

    Args:
        pipeline (Pipeline): Component container; speech clients are created only as needed.
        data (str | Path | bytes): Question text, audio file path, or audio bytes.
        mode (Literal["STT", "TTS", "full", "only text"]): Processing mode.
        stop (str): Nonblank tour-stop name for routing and retrieval.
        mime_type (str | None): Optional audio MIME type; required for audio bytes.
        voice (str): Speech voice identifier; defaults to "Kore".
        context (list[str] | None): Optional additional nonblank context.
        language (Literal["en", "es"]): Answer language; defaults to "en".
        request_type (Literal["historic", "restaurant"] | None): Explicit topic;
            defaults to None for classification.

    Returns:
        str | bytes: Generated text for text-output modes or WAV bytes for speech output.

    Raises:
        pydantic.ValidationError: Inputs violate field or mode-specific constraints.
        TypeError: Transcription does not yield text.
        ValueError: Configuration is invalid or no matching chunks exist.
        RuntimeError: Retrieval, generation, or audio output is unusable.
        OSError: A required file or provider connection cannot be accessed.
        sqlite3.Error: Local retrieval fails.
        yaml.YAMLError: Prompt configuration cannot be parsed.
        google.api_core.exceptions.GoogleAPIError: A cloud dependency fails.
    """
    request = PipelineRequest(
        data=data,
        mode=mode,
        stop=stop,
        mime_type=mime_type,
        voice=voice,
        context=[] if context is None else context,
        language=language,
        request_type=request_type,
    )
    started = perf_counter()
    logger.info(
        "Pipeline started",
        extra={"event": "pipeline.started", "mode": request.mode, "language": request.language},
    )
    query = request.data
    if request.mode in ("STT", "full"):
        report_progress("transcribing")
        # Text-only requests must not initialize an unused transcription dependency.
        if pipeline.stt is None:
            pipeline.stt = STT()
        query = pipeline.stt.transcribe(request.data, mime_type=request.mime_type)
    if not isinstance(query, str):
        raise TypeError("The agent pipeline requires a text query.")
    # Speech and text modes share the same grounded answer-generation path.
    answer = pipeline.agent_pipeline.run(
        request.stop, user_query=query, param=request.request_type,
        context=request.context, language=request.language
    )
    if request.mode in ("TTS", "full"):
        report_progress("synthesizing")
        if pipeline.tts is None:
            pipeline.tts = TTS()
        result: str | bytes = pipeline.tts.synthesize(answer, voice=request.voice)
    else:
        result = answer
    logger.info(
        "Pipeline completed",
        extra={
            "event": "pipeline.completed", "mode": request.mode, "language": request.language,
            "duration_ms": round((perf_counter() - started) * 1000, 3),
        },
    )
    return result
