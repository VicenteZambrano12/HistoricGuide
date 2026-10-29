from pydantic import BaseModel, ConfigDict

from src.utils.AgentSystem.Orchestrator.dataclasses.types import NonEmptyText


class GenerationResponse(BaseModel):
    """Validate and trim a generated answer before returning it to the pipeline.

    Args:
        text (str): Required nonblank generated answer.

    Returns:
        GenerationResponse: Validated answer text.

    Raises:
        pydantic.ValidationError: Text is invalid or extra fields are supplied.
    """

    model_config = ConfigDict(extra="forbid")

    # Empty or non-string model output is rejected rather than returned as an answer.
    text: NonEmptyText
