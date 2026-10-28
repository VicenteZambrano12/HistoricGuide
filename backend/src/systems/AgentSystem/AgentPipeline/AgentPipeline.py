"""Text-to-text tour pipeline: route a request, then generate its answer."""

from dataclasses import dataclass, field

from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator
from src.systems.AgentSystem.ResponseGenerator.ResponseGenerator import ResponseGenerator
from src.utils.AgentSystem.AgentPipeline.run import run
from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language


@dataclass
class AgentPipeline:
    orchestrator: Orchestrator = field(default_factory=Orchestrator)
    response_generator: ResponseGenerator = field(default_factory=ResponseGenerator)

    def run(
        self,
        stop: str,
        *,
        user_query: str | None = None,
        param: Category | None = None,
        context: list[str] | None = None,
        language: Language = "en",
    ) -> str:
        """Return answer text for a query or an explicitly selected category."""
        return run(
            self, stop, user_query=user_query, param=param,
            context=context, language=language,
        )