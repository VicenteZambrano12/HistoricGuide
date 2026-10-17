from pydantic import BaseModel, ConfigDict

from .types import NonEmptyText


class OrchestratorPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_prompt: NonEmptyText
