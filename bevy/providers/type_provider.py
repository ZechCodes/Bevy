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
    """The type provider supports any class type and will attempt to instantiate them with no args if they aren't found
    in the repository's cache.

    **Example**

        class Demo:
            ...

        @inject
        def example(arg: Demo = dependency()):
            ...
    """

    def factory(self, key: Type[_T], _) -> Option[Callable[[], _T]]:
        """Returns a constructor callable if the key is a class type. The `__bevy_constructor__` method is used when
        implemented by the class type, otherwise the class type will be returned.
        """
        match key:
            case BevyConstructable() as type_ if isinstance(type_, type):
                return Value(type_.__bevy_constructor__)
            case type() as type_:
                return Value(type_)
            case _:
                return Null()

    def supports(self, key: Type[_T], _) -> bool:
        """Only allows the `TypeProvider` to work with class types."""
        return isinstance(key, type)
