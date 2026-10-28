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
        if pipeline.stt is None:
            pipeline.stt = STT()
        query = pipeline.stt.transcribe(request.data, mime_type=request.mime_type)
    if not isinstance(query, str):
        raise TypeError("The agent pipeline requires a text query.")
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
