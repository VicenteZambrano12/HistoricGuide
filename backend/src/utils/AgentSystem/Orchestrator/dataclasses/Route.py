from .Classification import Classification
from .types import NonEmptyText


class Route(Classification):
    stop: NonEmptyText
