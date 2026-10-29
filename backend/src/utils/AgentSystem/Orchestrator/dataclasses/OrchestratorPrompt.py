from pydantic import BaseModel, ConfigDict

from .types import NonEmptyText


class OrchestratorPrompt(BaseModel):
    """Validate the classifier's system prompt loaded from configuration.

    Args:
        system_prompt (str): Required nonblank classification instruction.

    Returns:
        OrchestratorPrompt: Validated prompt configuration.

    Raises:
        pydantic.ValidationError: The prompt is invalid or extra fields are supplied.
    """

    model_config = ConfigDict(extra="forbid")

    # Prompts must remain nonempty after trimming; implicit string coercion is disabled.
    system_prompt: NonEmptyText
