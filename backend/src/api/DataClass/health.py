from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Report that the API process can respond to a liveness request."""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})

    status: Literal["ok"] = Field(
        ...,
        description="Process-liveness status; does not verify external dependencies.",
        examples=["ok"],
    )
