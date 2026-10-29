from pydantic import BaseModel, ConfigDict, model_validator

from .types import Category, NonEmptyText


class RoutingRequest(BaseModel):
    """Require exactly one routing input for a nonblank tour stop.

    Args:
        stop (str): Required nonblank stop name.
        user_query (str | None): Nonblank text to classify; defaults to None.
        param (Literal["historic", "restaurant"] | None): Explicit category;
            defaults to None and is mutually exclusive with user_query.

    Returns:
        RoutingRequest: Validated classifier input.

    Raises:
        pydantic.ValidationError: Fields are invalid, extra, or violate input exclusivity.
    """

    model_config = ConfigDict(extra="forbid")

    # Stop names are strict strings, stripped of whitespace, and nonempty.
    stop: NonEmptyText
    # None delegates selection to param; supplied query text must be nonblank.
    user_query: NonEmptyText | None = None
    # An explicit topic bypasses classification and cannot accompany a routing query.
    param: Category | None = None

    @model_validator(mode="after")
    def require_one_input(self) -> "RoutingRequest":
        """Enforce exclusive selection between classification and an explicit topic.

        Args:
            None.

        Returns:
            RoutingRequest: The validated request instance.

        Raises:
            ValueError: Both routing inputs are supplied or both are absent.
        """
        if (self.user_query is None) == (self.param is None):
            raise ValueError("Provide exactly one of user_query or param.")
        return self
