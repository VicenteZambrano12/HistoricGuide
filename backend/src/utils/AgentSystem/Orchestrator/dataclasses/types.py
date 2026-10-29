from typing import Annotated, Literal

from pydantic import StringConstraints


# External classifier labels must match these corpus topics exactly.
Category = Literal["historic", "restaurant"]
# Shared text fields reject coercion and whitespace-only content after trimming.
NonEmptyText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]
