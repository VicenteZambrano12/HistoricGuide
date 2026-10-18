from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ChatMode = Literal["stt", "tts", "full", "text"]
ChatLanguage = Literal["ES", "EN"]


class ChatResponse(BaseModel):
    """Deliver the guide's answer for text and speech-to-text chat modes."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "text": "The Pantheon's dome has an open oculus that lights the interior.",
        },
    })

    text: str = Field(
        ...,
        description=(
            "Generated guide answer in the requested language, not the raw "
            "transcription. Returned by text and stt modes."
        ),
        examples=["The Pantheon's dome has an open oculus that lights the interior."],
    )
