from typing import TYPE_CHECKING

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language

from .dataclasses.PipelineRequest import PipelineRequest

if TYPE_CHECKING:
    from src.systems.AgentSystem.AgentPipeline.AgentPipeline import AgentPipeline


def run(
    pipeline: "AgentPipeline",
    stop: str,
    *,
    user_query: str | None = None,
    param: Category | None = None,
    context: list[str] | None = None,
    language: Language = "en",
) -> str:
    request = PipelineRequest(
        stop=stop,
        user_query=user_query,
        param=param,
        context=[] if context is None else context,
        language=language,
    )
    route = pipeline.orchestrator.route(
        request.stop, user_query=request.user_query, param=request.param
    )
    return pipeline.response_generator.generate(
        route.stop,
        route.category,
        user_query=request.user_query,
        context=request.context,
        language=request.language,
    )
