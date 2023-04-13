from bevy.providers import Provider, Builder
from typing import Type, TypeVar


T = TypeVar("_T")


class TypeProvider(Provider):
    """The type provider supports any types and will attempt to instantiate them with no args."""
    def builder(self, new_type: Type[T]) -> Builder | None:
        return lambda: new_type()
