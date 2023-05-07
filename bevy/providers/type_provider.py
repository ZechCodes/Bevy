from typing import Callable, Type, TypeVar, Protocol, runtime_checkable

from bevy.options import Option, Null, Value
from bevy.providers.provider import Provider

_T = TypeVar("_T")


@runtime_checkable
class BevyConstructable(Protocol[_T]):
    @classmethod
    def __bevy_constructor__(cls: Type[_T], *args, **kwargs) -> _T:
        ...


class TypeProvider(Provider[Type[_T], _T]):
    """The type provider supports any types and will attempt to instantiate them with no args."""

    def factory(self, key: Type[_T], _) -> Option[Callable[[], _T]]:
        """Return a constructor callable for the key if it's a type. This will look for special dunder bevy constructor
        methods which will be preferred over the type callable."""
        match key:
            case BevyConstructable() as type_ if isinstance(type_, type):
                return Value(type_.__bevy_constructor__)
            case type() as type_:
                return Value(type_)
            case _:
                return Null()

    def supports(self, key: Type[_T], _) -> bool:
        """Returns True only if the key is a type."""
        return isinstance(key, type)
