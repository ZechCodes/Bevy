from bevy.providers import Provider
from typing import Callable, Type, TypeVar


_T = TypeVar("_T")


class TypeProvider(Provider[Type[_T], _T]):
    """The type provider supports any types and will attempt to instantiate them with no args."""

    def factory(self, new_type: Type[_T]) -> Callable[[], _T] | None:
        return lambda: new_type()
