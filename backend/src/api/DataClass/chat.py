from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from src.utils.general.sources import PdfSource


ChatMode = Literal["stt", "tts", "full", "text"]
ChatLanguage = Literal["ES", "EN"]


class ChatResponse(BaseModel):
    """Deliver an answer and its PDF provenance for text-output modes.

    Args:
        text (str): Generated answer in the requested language.
        sources (list[PdfSource]): PDF references; defaults to a new empty list.

    Returns:
        ChatResponse: Validated text-output response.

    Raises:
        pydantic.ValidationError: A required field is missing or has an invalid type.
    """

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "text": "The Pantheon's dome has an open oculus that lights the interior.",
            "sources": [],
        },
    })

    # Answer text is required; this schema imposes no minimum string length.
    text: str = Field(
        ...,
        description=(
            "Generated guide answer in the requested language, not the raw "
            "transcription. Returned by text and stt modes."
        ),
        examples=["The Pantheon's dome has an open oculus that lights the interior."],
    )
    # Each response owns its reference list; nested references validate page numbers.
    sources: list[PdfSource] = Field(
        default_factory=list,
        description="Retrieved PDF references with one-based page numbers.",
        examples=[[{"source": "Pantheon/historic/guide.pdf", "page": 2}]],
    )
