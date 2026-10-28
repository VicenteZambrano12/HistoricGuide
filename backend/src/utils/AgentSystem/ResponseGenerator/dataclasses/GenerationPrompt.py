from pydantic import BaseModel, ConfigDict

from src.utils.AgentSystem.Orchestrator.dataclasses.types import NonEmptyText


class GenerationPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_prompt: NonEmptyText
