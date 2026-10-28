"""Validate and route tour requests without generating user-facing answers."""

from dataclasses import dataclass

from src.utils.general.GeminiApiCall import GeminiClient

from src.utils.AgentSystem.Orchestrator.dataclasses.Route import Route
from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.AgentSystem.Orchestrator.route import route


@dataclass
class Orchestrator:
    client: GeminiClient | None = None

    def route(
        self,
        stop: str,
        *,
        user_query: str | None = None,
        param: Category | None = None,
    ) -> Route:
        """Return a stop/category destination; explicit parameters bypass Gemini."""
        return route(self, stop, user_query=user_query, param=param)