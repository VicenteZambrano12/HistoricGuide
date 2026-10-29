from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Represent process liveness independently of external dependencies.

    Args:
        status (Literal["ok"]): Required process-liveness marker.

    Returns:
        HealthResponse: Validated liveness response.

    Raises:
        pydantic.ValidationError: The status is missing or differs from "ok".
    """

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})

    # Only the literal "ok" is valid; callers must supply it explicitly.
    status: Literal["ok"] = Field(
        ...,
        description="Process-liveness status; does not verify external dependencies.",
        examples=["ok"],
    )
