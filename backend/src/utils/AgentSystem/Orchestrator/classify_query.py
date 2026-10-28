import json

from src.utils.general.GeminiApiCall import GeminiClient

from .dataclasses.Classification import Classification
from .dataclasses.OrchestratorPrompt import OrchestratorPrompt
from .dataclasses.RoutingRequest import RoutingRequest
from .dataclasses.types import Category


def classify_query(
    client: GeminiClient, request: RoutingRequest, prompt: OrchestratorPrompt
) -> Category:
    label = client.generate(
        json.dumps(
            {"stop": request.stop, "user_query": request.user_query},
            ensure_ascii=False,
        ),
        system_prompt=prompt.system_prompt,
        response_mime_type="text/plain",
    )
    return Classification.model_validate({"category": label.strip()}).category
