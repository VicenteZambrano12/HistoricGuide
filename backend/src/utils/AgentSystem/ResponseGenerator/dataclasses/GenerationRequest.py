from pydantic import Field

from src.utils.AgentSystem.Orchestrator.dataclasses.Route import Route
from src.utils.AgentSystem.Orchestrator.dataclasses.types import NonEmptyText

from .types import Language


class GenerationRequest(Route):
    """Combine a routed destination with generation context and output language.

    Args:
        category (Literal["historic", "restaurant"]): Inherited routing category.
        stop (str): Inherited nonblank stop name.
        language (Literal["en", "es"]): Output language; defaults to "en".
        user_query (str | None): Optional nonblank question; defaults to None.
        context (list[str]): Nonblank supporting texts; defaults to a new empty list.

    Returns:
        GenerationRequest: Validated response-generation input.

    Raises:
        pydantic.ValidationError: Fields, list items, or extra fields are invalid.
    """

    # Only English and Spanish are accepted; omitted language selects English.
    language: Language = "en"
    # A missing question requests a category introduction; supplied text is trimmed.
    user_query: NonEmptyText | None = None
    # Each request owns a strict list of nonblank context strings.
    context: list[NonEmptyText] = Field(default_factory=list, strict=True)
