from bevy.providers import Provider, Builder
from typing import Type, TypeVar


T = TypeVar("T")


class GenericProvider(Provider):
    """The generic provider supports any types and will attempt to instantiate them with no args."""
    def builder(self, new_type: Type[T]) -> Builder | None:
        return lambda: new_type()