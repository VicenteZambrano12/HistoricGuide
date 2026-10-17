from pathlib import Path
from typing import TYPE_CHECKING

from src.systems.STT.STT import STT
from src.systems.TTS.TTS import TTS
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language

from .dataclasses.PipelineRequest import PipelineRequest
from .dataclasses.types import PipelineMode

if TYPE_CHECKING:
    from src.systems.Pipeline import Pipeline


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
) -> str | bytes:
    request = PipelineRequest(
        data=data,
        mode=mode,
        stop=stop,
        mime_type=mime_type,
        voice=voice,
        context=[] if context is None else context,
        language=language,
    )
    query = request.data
    if request.mode in ("STT", "full"):
        if pipeline.stt is None:
            pipeline.stt = STT()
        query = pipeline.stt.transcribe(request.data, mime_type=request.mime_type)
    if not isinstance(query, str):
        raise TypeError("The agent pipeline requires a text query.")
    answer = pipeline.agent_pipeline.run(
        request.stop, user_query=query, context=request.context, language=request.language
    )
    if request.mode in ("TTS", "full"):
        if pipeline.tts is None:
            pipeline.tts = TTS()
        return pipeline.tts.synthesize(answer, voice=request.voice)
    return answer
