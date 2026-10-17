from typing import Literal

from pydantic import BaseModel


ChatMode = Literal["stt", "tts", "full", "text"]
ChatLanguage = Literal["ES", "EN"]


class ChatResponse(BaseModel):
    text: str
