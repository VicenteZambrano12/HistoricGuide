"""Generate a user-facing answer for a routed tour request."""

from dataclasses import dataclass

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language
from src.utils.AgentSystem.ResponseGenerator.generate_response import generate_response
from src.utils.general.GeminiApiCall import GeminiClient


@dataclass
class ResponseGenerator:
    client: GeminiClient | None = None

    def generate(
        self,
        stop: str,
        category: Category,
        *,
        user_query: str | None = None,
        context: list[str] | None = None,
        language: Language = "en",
    ) -> str:
        """Answer using the category prompt and optional retrieved text chunks."""
        return generate_response(
            self, stop, category, user_query=user_query, context=context, language=language
        )