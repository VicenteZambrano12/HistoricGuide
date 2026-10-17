from typing import TYPE_CHECKING

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.general.GeminiApiCall import GeminiClient

from .dataclasses.GenerationRequest import GenerationRequest
from .dataclasses.GenerationResponse import GenerationResponse
from .dataclasses.types import Language
from .load_prompt import load_prompt

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
    text = generator.client.generate(
        request.model_dump_json(),
        system_prompt=prompt.system_prompt,
        response_mime_type="text/plain",
    )
    return GenerationResponse.model_validate({"text": text}).text
