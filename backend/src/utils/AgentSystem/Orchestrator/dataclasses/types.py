from typing import Annotated, Literal

from pydantic import StringConstraints


Category = Literal["historic", "restaurant"]
NonEmptyText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]
