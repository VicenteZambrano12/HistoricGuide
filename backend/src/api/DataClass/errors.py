from pydantic import BaseModel, ConfigDict, Field


class HTTPErrorResponse(BaseModel):
    """Describe an HTTP error without changing the application's error handlers."""

    model_config = ConfigDict(json_schema_extra={
        "example": {"detail": "Audio must not exceed 14000000 bytes."},
    })

    detail: str = Field(
        ...,
        description="Human-readable reason the request could not be processed.",
        examples=["Audio must not exceed 14000000 bytes."],
    )


class ValidationIssue(BaseModel):
    """Locate and explain one invalid request value."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "loc": ["body", "stop"],
            "msg": "Field required",
            "type": "missing",
        },
    })

    loc: list[str | int] = Field(
        ...,
        description="Request location followed by field names or collection indexes.",
        examples=[["body", "stop"]],
    )
    msg: str = Field(
        ...,
        description="Human-readable explanation of the validation failure.",
        examples=["Field required"],
    )
    type: str = Field(
        ...,
        description="Machine-readable validation error identifier.",
        examples=["missing"],
    )


class RequestValidationErrorResponse(BaseModel):
    """Document both automatic validation and explicit chat input rejections."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "detail": [{
                "loc": ["body", "stop"],
                "msg": "Field required",
                "type": "missing",
            }],
        },
    })

    detail: str | list[ValidationIssue] = Field(
        ...,
        description=(
            "An explicit input-error message or automatic validation issues. "
            "Issues may also include input values and validation context."
        ),
        examples=[
            "stt and full modes require an audio file.",
            [{"loc": ["body", "stop"], "msg": "Field required", "type": "missing"}],
        ],
    )
