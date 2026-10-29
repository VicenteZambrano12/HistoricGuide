from typing import TYPE_CHECKING

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.general.GeminiApiCall import GeminiClient
from src.utils.general.progress import report_progress

from .dataclasses.GenerationRequest import GenerationRequest
from .dataclasses.GenerationResponse import GenerationResponse
from .dataclasses.types import Language
from .load_prompt import load_prompt
from .retrieve_chunks import retrieve_chunks

if TYPE_CHECKING:
    from src.systems.AgentSystem.ResponseGenerator.ResponseGenerator import ResponseGenerator


def generate_response(
    generator: "ResponseGenerator",
    stop: str,
    category: Category,
    *,
    user_query: str | None = None,
    context: list[str] | None = None,
    language: Language = "en",
) -> str:
    """Retrieve supporting excerpts and generate a validated, language-specific answer.

    Args:
        generator (ResponseGenerator): Service retaining its provider client and database path.
        stop (str): Nonblank tour-stop name.
        category (Literal["historic", "restaurant"]): Corpus and prompt topic.
        user_query (str | None): Optional question; None requests an introduction.
        context (list[str] | None): Optional nonblank caller-provided supporting text.
        language (Literal["en", "es"]): Answer language; defaults to "en".

    Returns:
        str: Nonblank generated answer with surrounding whitespace removed.

    Raises:
        pydantic.ValidationError: Request, prompt, provenance, or answer is invalid.
        ValueError: Configuration is invalid or no matching chunks exist.
        RuntimeError: Retrieval metadata, vectors, or generation output are unusable.
        OSError: Local resources or provider connections cannot be accessed.
        sqlite3.Error: Local retrieval fails.
        yaml.YAMLError: The generation prompt cannot be parsed.
        google.api_core.exceptions.GoogleAPIError: Cloud prompt retrieval fails.
        qdrant_client.http.exceptions.UnexpectedResponse: Qdrant rejects retrieval.
        qdrant_client.http.exceptions.ResponseHandlingException: Qdrant transport fails.
    """
    request = GenerationRequest(
        stop=stop,
        category=category,
        user_query=user_query,
        context=[] if context is None else context,
        language=language,
    )
    prompt = load_prompt(request.category)
    if generator.client is None:
        generator.client = GeminiClient(max_output_tokens=1024)
    report_progress("retrieving")
    chunks = retrieve_chunks(
        generator.client,
        request.stop,
        request.category,
        user_query=request.user_query,
        database_path=generator.database_path,
    )
    # Ground the serialized generation request in both supplied and retrieved evidence.
    request.context.extend(chunks)
    report_progress("generating")
    text = generator.client.generate(
        request.model_dump_json(),
        system_prompt=prompt.system_prompt,
        response_mime_type="text/plain",
    )
    return GenerationResponse.model_validate({"text": text}).text
