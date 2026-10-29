from pydantic import BaseModel, ConfigDict

from .types import Category


class Classification(BaseModel):
    """Validate a routing category and reject undocumented response fields.

    Args:
        category (Literal["historic", "restaurant"]): Required routing destination.

    Returns:
        Classification: Validated topic selection.

    Raises:
        pydantic.ValidationError: The category is invalid or extra fields are supplied.
    """

    model_config = ConfigDict(extra="forbid")

    # The classifier must emit one supported topic, not free-form prose.
    category: Category
