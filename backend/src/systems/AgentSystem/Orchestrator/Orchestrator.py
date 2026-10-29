"""Validate and route tour requests without generating user-facing answers."""

from dataclasses import dataclass

from src.utils.general.GeminiApiCall import GeminiClient

from src.utils.AgentSystem.Orchestrator.dataclasses.Route import Route
from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.AgentSystem.Orchestrator.route import route


@dataclass
class Orchestrator:
    """Select the historical or restaurant route without generating an answer.

    Args:
        client (GeminiClient | None): Optional classifier client; defaults to None
            and is initialized only when classification is required.

    Returns:
        Orchestrator: Reusable topic-routing service.

    Raises:
        None.
    """

    client: GeminiClient | None = None

    def route(
        self,
        stop: str,
        *,
        user_query: str | None = None,
        param: Category | None = None,
    ) -> Route:
        """Select a destination, bypassing Gemini when an explicit topic is supplied.

        Args:
            stop (str): Nonblank tour-stop name.
            user_query (str | None): Nonblank classification input; defaults to None.
            param (Literal["historic", "restaurant"] | None): Explicit topic; defaults
                to None and must be mutually exclusive with user_query.

        Returns:
            Route: Validated destination containing the stop and selected category.

        Raises:
            pydantic.ValidationError: Routing input, prompt, or classifier output is invalid.
            ValueError: Provider or shared configuration is invalid.
            RuntimeError: Gemini produces no usable classification.
            OSError: Prompt files or the provider connection cannot be accessed.
            yaml.YAMLError: The classifier prompt cannot be parsed.
            google.api_core.exceptions.GoogleAPIError: Cloud prompt retrieval fails.
        """
        return route(self, stop, user_query=user_query, param=param)