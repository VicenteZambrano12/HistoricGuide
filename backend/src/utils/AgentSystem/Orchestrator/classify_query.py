import json

from src.utils.general.GeminiApiCall import GeminiClient

from .dataclasses.Classification import Classification
from .dataclasses.OrchestratorPrompt import OrchestratorPrompt
from .dataclasses.RoutingRequest import RoutingRequest
from .dataclasses.types import Category


def classify_query(
    client: GeminiClient, request: RoutingRequest, prompt: OrchestratorPrompt
) -> Category:
    """Classify a validated question into the supported routing categories.

    Args:
        client (GeminiClient): Configured classification provider client.
        request (RoutingRequest): Validated stop and classification query.
        prompt (OrchestratorPrompt): System instruction constraining the classifier label.

    Returns:
        Literal["historic", "restaurant"]: Validated category selected by Gemini.

    Raises:
        pydantic.ValidationError: The generated label is not a supported category.
        ValueError: The configured prompt is invalid.
        RuntimeError: Gemini returns no usable text.
        OSError: The provider connection fails or times out.
        json.JSONDecodeError: The provider response is not valid JSON.
    """
    label = client.generate(
        json.dumps(
            {"stop": request.stop, "user_query": request.user_query},
            ensure_ascii=False,
        ),
        system_prompt=prompt.system_prompt,
        response_mime_type="text/plain",
    )
    # Invalid labels must fail validation rather than silently selecting a corpus.
    return Classification.model_validate({"category": label.strip()}).category
