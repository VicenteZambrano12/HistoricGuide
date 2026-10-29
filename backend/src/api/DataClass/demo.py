from typing import Literal

from pydantic import BaseModel, Field


DemoFailureReason = Literal[
    "unreachable", "collection_missing", "collection_empty",
    "collection_incompatible", "configuration", "startup_failed",
]


class DemoStatus(BaseModel):
    """Expose dependency readiness without credentials or provider error details.

    Args:
        status (Literal["ready", "starting", "waiting", "unavailable"]): Readiness state.
        reason (DemoFailureReason | None): Supported failure code; defaults to None.
        retryable (bool): Whether retrying may help; defaults to False.

    Returns:
        DemoStatus: Validated public readiness result.

    Raises:
        pydantic.ValidationError: A status, reason, or field type is invalid.
    """

    # The required state is restricted to the four public lifecycle values.
    status: Literal["ready", "starting", "waiting", "unavailable"] = Field(
        description="Whether the guide can use its document collection.",
    )
    # Failures expose only allowlisted codes; None denotes the absence of a reason.
    reason: DemoFailureReason | None = Field(
        default=None, description="Safe reason code for a startup or readiness failure.",
    )
    # Retries are disabled unless an endpoint explicitly identifies a transient failure.
    retryable: bool = Field(default=False, description="Whether a bounded startup retry may help.")
