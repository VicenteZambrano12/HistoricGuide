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
    request = RoutingRequest(stop=stop, user_query=user_query, param=param)
    category = request.param
    if category is None:
        prompt = load_prompt()
        if orchestrator.client is None:
            orchestrator.client = GeminiClient()
        category = classify_query(orchestrator.client, request, prompt)
    return Route(stop=request.stop, category=category)
