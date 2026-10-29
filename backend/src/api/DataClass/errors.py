from pydantic import BaseModel, ConfigDict, Field


class HTTPErrorResponse(BaseModel):
    """Describe an HTTP rejection using the application's JSON error shape.

    Args:
        detail (str): Required human-readable error message.

    Returns:
        HTTPErrorResponse: Validated error description.

    Raises:
        pydantic.ValidationError: The detail is missing or is not a valid string.
    """

    model_config = ConfigDict(json_schema_extra={
        "example": {"detail": "Audio must not exceed 14000000 bytes."},
    })

    # Error details are required strings without additional length constraints.
    detail: str = Field(
        ...,
        description="Human-readable reason the request could not be processed.",
        examples=["Audio must not exceed 14000000 bytes."],
    )


class ValidationIssue(BaseModel):
    """Locate and describe one request validation failure.

    Args:
        loc (list[str | int]): Request scope, field names, and collection indexes.
        msg (str): Explanation of the rejected value.
        type (str): Machine-readable validation error code.

    Returns:
        ValidationIssue: Validated description of one invalid input.

    Raises:
        pydantic.ValidationError: A required field is missing or has an invalid type.
    """

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "loc": ["body", "stop"],
            "msg": "Field required",
            "type": "missing",
        },
    })

    # Location components are field names or numeric collection indexes.
    loc: list[str | int] = Field(
        ...,
        description="Request location followed by field names or collection indexes.",
        examples=[["body", "stop"]],
    )
    # Explanatory text is required; the model does not constrain its wording.
    msg: str = Field(
        ...,
        description="Human-readable explanation of the validation failure.",
        examples=["Field required"],
    )
    # Error codes remain open-ended to support upstream validation rules.
    type: str = Field(
        ...,
        description="Machine-readable validation error identifier.",
        examples=["missing"],
    )


class RequestValidationErrorResponse(BaseModel):
    """Represent either an explicit rejection or structured validation issues.

    Args:
        detail (str | list[ValidationIssue]): Error text or field-level issues.

    Returns:
        RequestValidationErrorResponse: Validated request-error envelope.

    Raises:
        pydantic.ValidationError: The detail or any nested issue is invalid.
    """

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "detail": [{
                "loc": ["body", "stop"],
                "msg": "Field required",
                "type": "missing",
            }],
        },
    })

    # Explicit HTTP errors use strings; automatic validation uses nested issue objects.
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
