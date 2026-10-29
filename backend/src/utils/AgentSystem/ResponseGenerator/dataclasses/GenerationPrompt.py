from pydantic import BaseModel, ConfigDict

from src.utils.AgentSystem.Orchestrator.dataclasses.types import NonEmptyText


class GenerationPrompt(BaseModel):
    """Validate the system instructions for a response-generation category.

    Args:
        system_prompt (str): Required nonblank generation instruction.

    Returns:
        GenerationPrompt: Validated prompt configuration.

    Raises:
        pydantic.ValidationError: The prompt is invalid or extra fields are supplied.
    """

    model_config = ConfigDict(extra="forbid")

    # Strict, trimmed text prevents an empty system instruction from reaching Gemini.
    system_prompt: NonEmptyText
