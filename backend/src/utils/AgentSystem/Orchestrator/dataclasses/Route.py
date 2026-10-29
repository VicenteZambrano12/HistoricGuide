from .Classification import Classification
from .types import NonEmptyText


class Route(Classification):
    """Associate a validated category with a nonblank tour stop.

    Args:
        category (Literal["historic", "restaurant"]): Inherited routing destination.
        stop (str): Required stop name, stripped of surrounding whitespace.

    Returns:
        Route: Validated stop/category destination.

    Raises:
        pydantic.ValidationError: A category, stop, or extra field is invalid.
    """

    # Strict string validation rejects coercion and empty values after trimming.
    stop: NonEmptyText
