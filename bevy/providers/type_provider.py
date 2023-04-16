from typing import Callable, Type, TypeVar, Protocol, runtime_checkable

from bevy.options import Option, Null, Value
from bevy.providers.base import Provider

_T = TypeVar("_T")


@runtime_checkable
class BevyConstructable(Protocol[_T]):
    @classmethod
    def __bevy_constructor__(cls: Type[_T], *args, **kwargs) -> _T:
        ...


class TypeProvider(Provider[Type[_T], _T]):
    """The type provider supports any types and will attempt to instantiate them with no args."""

    def factory(self, new_type: Type[_T]) -> Option[Callable[[], _T]]:
        match new_type:
            case BevyConstructable():
                return Value(new_type.__bevy_constructor__)
            case type():
                return Value(new_type)
            case _:
                return Null()

    def supports(self, new_type: Type[_T]) -> bool:
        return isinstance(new_type, type)
