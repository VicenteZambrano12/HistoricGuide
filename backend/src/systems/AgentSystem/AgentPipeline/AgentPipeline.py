"""Text-to-text tour pipeline: route a request, then generate its answer."""

from dataclasses import dataclass, field

from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator
from src.systems.AgentSystem.ResponseGenerator.ResponseGenerator import ResponseGenerator
from src.utils.AgentSystem.AgentPipeline.run import run
from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language


@dataclass
class AgentPipeline:
    """Compose topic routing and grounded answer generation.

    Args:
        orchestrator (Orchestrator): Routing service; defaults to a new instance.
        response_generator (ResponseGenerator): Answer service; defaults to a new instance.

    Returns:
        AgentPipeline: Text-to-text guide pipeline with injectable components.

    Raises:
        None: Default components defer provider initialization until processing.
    """

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
        """Route a query or explicit topic and generate its grounded answer.

        Args:
            stop (str): Nonblank tour-stop name.
            user_query (str | None): Optional nonblank user question.
            param (Literal["historic", "restaurant"] | None): Explicit routing category;
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
        return run(
            self, stop, user_query=user_query, param=param,
            context=context, language=language,
        )