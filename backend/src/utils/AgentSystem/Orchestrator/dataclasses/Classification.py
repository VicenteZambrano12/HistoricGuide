from pydantic import BaseModel, ConfigDict

from .types import Category


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
