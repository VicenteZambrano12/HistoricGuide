from typing import TYPE_CHECKING

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language
from src.utils.general.progress import report_progress

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
    """Route validated agent input and pass its context to answer generation.

    Args:
        pipeline (AgentPipeline): Routing and generation components.
        stop (str): Nonblank tour-stop name.
        user_query (str | None): Optional nonblank user question.
        param (Literal["historic", "restaurant"] | None): Optional explicit category;
            at least one of param or user_query must be supplied.
        context (list[str] | None): Optional nonblank supporting text.
        language (Literal["en", "es"]): Answer language; defaults to "en".

    Returns:
        str: Validated generated answer.

    Raises:
        pydantic.ValidationError: Input, prompt, routing, or generated text is invalid.
        ValueError: Configuration is invalid or no matching chunks exist.
        RuntimeError: Retrieval or generation returns unusable results.
        OSError: Local resources or provider connections cannot be accessed.
        sqlite3.Error: Local retrieval fails.
        yaml.YAMLError: Prompt configuration cannot be parsed.
        google.api_core.exceptions.GoogleAPIError: A cloud dependency fails.
    """
    request = PipelineRequest(
        stop=stop,
        user_query=user_query,
        param=param,
        context=[] if context is None else context,
        language=language,
    )
    report_progress("routing")
    # An explicit topic bypasses classification without discarding the question for generation.
    route = pipeline.orchestrator.route(
        request.stop,
        user_query=request.user_query if request.param is None else None,
        param=request.param,
    )
    return pipeline.response_generator.generate(
        route.stop,
        route.category,
        user_query=request.user_query,
        context=request.context,
        language=request.language,
    )
