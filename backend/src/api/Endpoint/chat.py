import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from src.api.DataClass.chat import ChatLanguage, ChatMode, ChatResponse
from src.api.DataClass.errors import HTTPErrorResponse, RequestValidationErrorResponse
from src.api.Endpoint.chat_stream import stream_chat
from src.systems.Pipeline import Pipeline
from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category, NonEmptyText
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language
from src.utils.Pipeline.dataclasses.types import PipelineMode
from src.utils.general.sources import collecting_sources


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
    summary="Generate a tour guide answer",
    status_code=status.HTTP_200_OK,
    response_model=ChatResponse,
    response_model_exclude_defaults=True,
    response_description="Guide answer as JSON for text/stt or WAV audio for tts/full.",
    responses={
        status.HTTP_200_OK: {
            "content": {
                "application/json": {
                    "example": {
                        "text": "The Pantheon's dome has an open oculus that lights the interior.",
                    },
                },
                "audio/wav": {"schema": {"type": "string", "format": "binary"}},
                "application/x-ndjson": {
                    "schema": {"type": "string"},
                    "example": '{"type":"progress","step":"routing"}\n'
                               '{"type":"result","text":"Guide answer."}\n',
                },
            },
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": HTTPErrorResponse,
            "description": "The multipart request body could not be parsed.",
            "content": {"application/json": {
                "example": {"detail": "Missing boundary in multipart."},
            }},
        },
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "model": HTTPErrorResponse,
            "description": "The uploaded audio exceeds 14,000,000 bytes.",
            "content": {"application/json": {
                "example": {"detail": "Audio must not exceed 14000000 bytes."},
            }},
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": RequestValidationErrorResponse,
            "description": (
                "A field is missing or invalid, or query does not match the mode. "
                "Audio must be nonempty and declare an audio/* MIME type."
            ),
            "content": {"application/json": {"examples": {
                "missing_stop": {
                    "summary": "Required stop omitted",
                    "value": {"detail": [{
                        "loc": ["body", "stop"],
                        "msg": "Field required",
                        "type": "missing",
                    }]},
                },
                "audio_required": {
                    "summary": "Text submitted to an audio-input mode",
                    "value": {"detail": "stt and full modes require an audio file."},
                },
            }}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": (
                "An unhandled pipeline, upstream service, or server failure occurred. "
                "No successful answer is returned."
            ),
            "content": {"text/plain": {
                "schema": {"type": "string"},
                "example": "Internal Server Error",
            }},
        },
    },
)
def chat(
    query: Annotated[str | UploadFile, File(
        description=(
            "Nonempty question text for text/tts, or a nonempty audio file for "
            "stt/full. Files must declare audio/* and be at most 14,000,000 bytes."
        ),
        examples=["Tell me about the Pantheon's dome."],
    )],
    mode: Annotated[ChatMode, Form(
        description=(
            "text: text to JSON answer; stt: audio to JSON answer; "
            "tts: text to WAV answer; full: audio to WAV answer. "
            "Every mode runs the agent pipeline."
        ),
        examples=["text"],
    )],
    language: Annotated[ChatLanguage, Form(
        description="Answer language: EN for English or ES for Spanish.",
        examples=["EN"],
    )],
    stop: Annotated[NonEmptyText, Form(
        description="Nonempty tour-stop name used to contextualize the guide's answer.",
        examples=["Pantheon"],
    )],
    request_type: Annotated[Category | None, Form(
        description=(
            "Explicit topic: historic or restaurant. Omit to classify the query automatically."
        ),
        examples=["historic"],
    )] = None,
    stream: Annotated[bool, Form(
        description="Stream NDJSON progress events followed by a result or error event.",
        examples=[True],
    )] = False,
) -> ChatResponse | Response:
    """Answer a historical or restaurant question about a tour stop.

    **Permissions:** Public; no client credentials are required. The server
    requires a configured `GEMINI_API_KEY`.

    Submit **multipart/form-data** with query, mode, language, and stop.
    Optionally select `request_type` (historic or restaurant) to bypass automatic
    topic classification. `text` and `tts`
    require nonblank text; `stt` and `full` require a nonempty uploaded file
    declaring an `audio/*` MIME type, limited to 14,000,000 bytes inclusive.
    The stop must contain non-whitespace text and the language must be `EN`
    or `ES`.

    All modes execute the agent pipeline; audio-input modes first transcribe
    the question. `text` and `stt` return the generated answer as JSON, not a
    raw transcription. `tts` and `full` synthesize the answer as `audio/wav`.

    **Side effects:** Processing invokes external Gemini services and may incur
    provider usage charges. By default this is a synchronous operation.
    Set `stream=true` for newline-delimited JSON progress events, followed by
    a result containing `text` or base64 `audio` with `mime_type=audio/wav`.
    Results include `sources` with PDF paths relative to the document corpus and
    one-based page numbers. Non-streaming WAV replies carry the same references
    as JSON in the `X-PDF-Sources` header. Open PDFs through `/documents/{source}`.
    Processing failures after streaming begins produce an explicit `error` event.
    Invalid input is rejected before the pipeline is constructed; unhandled
    pipeline failures propagate as server errors.
    """
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

    def run_pipeline() -> str | bytes:
        return Pipeline().run(
            data,
            PIPELINE_MODES[mode],
            stop=stop,
            mime_type=mime_type,
            language=PIPELINE_LANGUAGES[language],
            request_type=request_type,
        )

    if stream:
        return stream_chat(run_pipeline, audio_output=mode in ("tts", "full"))
    with collecting_sources() as sources:
        result = run_pipeline()
    if mode in ("tts", "full"):
        if not isinstance(result, bytes):
            raise TypeError("The pipeline must return WAV bytes for tts and full modes.")
        return Response(
            content=result, media_type="audio/wav",
            headers={"X-PDF-Sources": json.dumps([source.model_dump() for source in sources])},
        )
    if not isinstance(result, str):
        raise TypeError("The pipeline must return text for text and stt modes.")
    return ChatResponse(text=result, sources=sources)
