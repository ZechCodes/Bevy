from typing import Callable, Type, TypeVar, Protocol, runtime_checkable

from bevy.providers import Provider

_T = TypeVar("_T")


@runtime_checkable
class BevyConstructable(Protocol[_T]):
    @classmethod
    def __bevy_constructor__(cls: Type[_T], *args, **kwargs) -> _T:
        ...


class TypeProvider(Provider[Type[_T], _T]):
    """The type provider supports any types and will attempt to instantiate them with no args."""

    def factory(self, new_type: Type[_T]) -> Callable[[], _T] | None:
        match new_type:
            case BevyConstructable():
                return new_type.__bevy_constructor__
            case _:
                return new_type
