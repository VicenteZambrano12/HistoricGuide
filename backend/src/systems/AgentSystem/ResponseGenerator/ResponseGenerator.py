"""Generate a user-facing answer for a routed tour request."""

from dataclasses import dataclass
from pathlib import Path

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language
from src.utils.AgentSystem.ResponseGenerator.generate_response import generate_response
from src.utils.AgentSystem.ResponseGenerator.retrieve_chunks import DEFAULT_DATABASE_PATH
from src.utils.general.GeminiApiCall import GeminiClient


@dataclass
class ResponseGenerator:
    """Generate answers grounded in stop/topic-filtered corpus excerpts.

    Args:
        client (GeminiClient | None): Optional provider client; defaults to None
            and is created when generation is first requested.
        database_path (Path): Local SQLite snapshot; defaults to DEFAULT_DATABASE_PATH.
            GCP retrieval uses configured Qdrant instead.

    Returns:
        ResponseGenerator: Reusable grounded-answer service.

    Raises:
        None.
    """

    client: GeminiClient | None = None
    database_path: Path = DEFAULT_DATABASE_PATH

    def generate(
        self,
        stop: str,
        category: Category,
        *,
        user_query: str | None = None,
        context: list[str] | None = None,
        language: Language = "en",
    ) -> str:
        """Answer using up to two retrieved chunks and caller-supplied context.

        Args:
            stop (str): Nonblank tour-stop name.
            category (Literal["historic", "restaurant"]): Corpus topic filter.
            user_query (str | None): Optional question; None requests an introduction.
            context (list[str] | None): Optional additional nonblank context.
            language (Literal["en", "es"]): Answer language; defaults to "en".

        Returns:
            str: Nonblank generated answer in the requested language.

        Raises:
            pydantic.ValidationError: Request, prompt, provenance, or answer is invalid.
            ValueError: Configuration is invalid or no matching chunks exist.
            RuntimeError: Retrieval metadata, vectors, or generation output are unusable.
            OSError: Local resources or provider connections cannot be accessed.
            sqlite3.Error: Local retrieval fails.
            yaml.YAMLError: The generation prompt cannot be parsed.
            google.api_core.exceptions.GoogleAPIError: Cloud prompt retrieval fails.
        """
        return generate_response(
            self, stop, category, user_query=user_query, context=context, language=language
        )