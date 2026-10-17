from pydantic import BaseModel, ConfigDict, model_validator

from .types import Category, NonEmptyText


class RoutingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stop: NonEmptyText
    user_query: NonEmptyText | None = None
    param: Category | None = None

    @model_validator(mode="after")
    def require_one_input(self) -> "RoutingRequest":
        if (self.user_query is None) == (self.param is None):
            raise ValueError("Provide exactly one of user_query or param.")
        return self
