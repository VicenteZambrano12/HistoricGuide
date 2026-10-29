from fastapi import APIRouter, status

from src.api.DataClass.errors import HTTPErrorResponse
from src.api.DataClass.health import HealthResponse


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Check API liveness",
    status_code=status.HTTP_200_OK,
    response_model=HealthResponse,
    response_description="The API process is responding.",
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": HTTPErrorResponse,
            "description": "An unexpected server failure prevented the liveness response.",
            "content": {"application/json": {
                "example": {"detail": "Internal Server Error"},
            }},
        },
    },
)
def health_check() -> HealthResponse:
    """Check whether the API process can serve requests.

    **Permissions:** Public; no credentials are required.

    This read-only operation makes no external service calls and has no side
    effects. A successful result does not verify Gemini configuration, network
    connectivity, or the readiness of the chat pipeline.

    Args:
        None.

    Returns:
        HealthResponse: The constant process-liveness status "ok".

    Raises:
        None.
    """
    return HealthResponse(status="ok")
