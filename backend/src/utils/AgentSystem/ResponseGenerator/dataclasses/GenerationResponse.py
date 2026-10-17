from pydantic import BaseModel, ConfigDict

from src.utils.AgentSystem.Orchestrator.dataclasses.types import NonEmptyText


class GenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: NonEmptyText
