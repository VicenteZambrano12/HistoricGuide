from pydantic import Field

from src.utils.AgentSystem.Orchestrator.dataclasses.Route import Route
from src.utils.AgentSystem.Orchestrator.dataclasses.types import NonEmptyText

from .types import Language


class GenerationRequest(Route):
    language: Language = "en"
    user_query: NonEmptyText | None = None
    context: list[NonEmptyText] = Field(default_factory=list, strict=True)
