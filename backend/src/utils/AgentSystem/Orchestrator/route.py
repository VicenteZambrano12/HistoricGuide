from typing import TYPE_CHECKING

from src.utils.general.GeminiApiCall import GeminiClient

from .dataclasses.Route import Route
from .dataclasses.RoutingRequest import RoutingRequest
from .dataclasses.types import Category
from .classify_query import classify_query
from .load_prompt import load_prompt

if TYPE_CHECKING:
    from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator


def route(
    orchestrator: "Orchestrator",
    stop: str,
    *,
    user_query: str | None = None,
    param: Category | None = None,
) -> Route:
    """Resolve a stop/category destination using explicit input or classification.

    Args:
        orchestrator (Orchestrator): Service retaining an optional reusable provider client.
        stop (str): Nonblank tour-stop name.
        user_query (str | None): Optional nonblank classification query.
        param (Literal["historic", "restaurant"] | None): Optional explicit topic;
            exactly one of param or user_query is required.

    Returns:
        Route: Validated destination containing the stop and selected category.

    Raises:
        pydantic.ValidationError: Request, prompt, classifier label, or route is invalid.
        ValueError: Provider or shared configuration is invalid.
        RuntimeError: Gemini returns no usable classification.
        OSError: Prompt files or the provider connection cannot be accessed.
        yaml.YAMLError: The classifier prompt cannot be parsed.
        google.api_core.exceptions.GoogleAPIError: Cloud prompt retrieval fails.
    """
    request = RoutingRequest(stop=stop, user_query=user_query, param=param)
    category = request.param
    # Explicit routing must avoid provider usage and classifier prompt loading.
    if category is None:
        prompt = load_prompt()
        if orchestrator.client is None:
            orchestrator.client = GeminiClient()
        category = classify_query(orchestrator.client, request, prompt)
    return Route(stop=request.stop, category=category)
