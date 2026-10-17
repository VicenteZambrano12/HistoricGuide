from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from src.api.DataClass.chat import ChatLanguage, ChatMode, ChatResponse
from src.systems.Pipeline import Pipeline
from src.utils.AgentSystem.Orchestrator.dataclasses.types import NonEmptyText
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language
from src.utils.Pipeline.dataclasses.types import PipelineMode


router = APIRouter(tags=["chat"])

PIPELINE_MODES: dict[ChatMode, PipelineMode] = {
    "stt": "STT",
    "tts": "TTS",
    "full": "full",
    "text": "only text",
}
PIPELINE_LANGUAGES: dict[ChatLanguage, Language] = {"ES": "es", "EN": "en"}
MAX_AUDIO_BYTES = 14_000_000


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={200: {"content": {"audio/wav": {"schema": {
        "type": "string", "format": "binary",
    }}}}},
)
def chat(
    query: Annotated[str | UploadFile, File()],
    mode: Annotated[ChatMode, Form()],
    language: Annotated[ChatLanguage, Form()],
    stop: Annotated[NonEmptyText, Form()],
) -> ChatResponse | Response:
    mime_type = None
    data: str | bytes
    if mode in ("stt", "full"):
        if isinstance(query, str):
            raise HTTPException(422, "stt and full modes require an audio file.")
        mime_type = query.content_type
        if mime_type is None or not mime_type.startswith("audio/"):
            raise HTTPException(422, "The query file must have an audio MIME type.")
        data = query.file.read(MAX_AUDIO_BYTES + 1)
        if not data:
            raise HTTPException(422, "The audio file must not be empty.")
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(413, f"Audio must not exceed {MAX_AUDIO_BYTES} bytes.")
    else:
        if not isinstance(query, str) or not query.strip():
            raise HTTPException(422, "text and tts modes require nonempty text.")
        data = query

    result = Pipeline().run(
        data,
        PIPELINE_MODES[mode],
        stop=stop,
        mime_type=mime_type,
        language=PIPELINE_LANGUAGES[language],
    )
    if mode in ("tts", "full"):
        if not isinstance(result, bytes):
            raise TypeError("The pipeline must return WAV bytes for tts and full modes.")
        return Response(content=result, media_type="audio/wav")
    if not isinstance(result, str):
        raise TypeError("The pipeline must return text for text and stt modes.")
    return ChatResponse(text=result)
