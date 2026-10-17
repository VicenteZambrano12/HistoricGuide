from pydantic import Field

from src.utils.AgentSystem.Orchestrator.dataclasses.RoutingRequest import RoutingRequest
from src.utils.AgentSystem.Orchestrator.dataclasses.types import NonEmptyText
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language


class PipelineRequest(RoutingRequest):
    language: Language = "en"
    context: list[NonEmptyText] = Field(default_factory=list, strict=True)
