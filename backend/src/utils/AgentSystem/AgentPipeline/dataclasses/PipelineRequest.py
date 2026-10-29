from pydantic import Field, model_validator

from src.utils.AgentSystem.Orchestrator.dataclasses.RoutingRequest import RoutingRequest
from src.utils.AgentSystem.Orchestrator.dataclasses.types import NonEmptyText
from src.utils.AgentSystem.ResponseGenerator.dataclasses.types import Language


class PipelineRequest(RoutingRequest):
    """Validate agent input while permitting an explicit topic with a question.

    Args:
        stop (str): Required nonblank stop name inherited from RoutingRequest.
        user_query (str | None): Optional nonblank question; defaults to None.
        param (Literal["historic", "restaurant"] | None): Optional explicit category;
            defaults to None.
        language (Literal["en", "es"]): Answer language; defaults to "en".
        context (list[str]): Nonblank supporting texts; defaults to a new empty list.

    Returns:
        PipelineRequest: Validated agent-pipeline input.

    Raises:
        pydantic.ValidationError: Fields are invalid, extra, or both inputs are absent.
    """

    # Only the configured English and Spanish output languages are accepted.
    language: Language = "en"
    # Strict list validation avoids coercing arbitrary iterables into request context.
    context: list[NonEmptyText] = Field(default_factory=list, strict=True)

    @model_validator(mode="after")
    def require_one_input(self) -> "PipelineRequest":
        """Require a question or topic without imposing routing-only exclusivity.

        Args:
            None.

        Returns:
            PipelineRequest: The validated request instance.

        Raises:
            ValueError: Neither user_query nor param is supplied.
        """
        if self.user_query is None and self.param is None:
            raise ValueError("Provide user_query or param.")
        return self
