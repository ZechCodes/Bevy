from typing import Callable, Protocol, Type, TypeVar, ParamSpec


T = TypeVar("T")
P = ParamSpec("P")


class Binder(Protocol[T]):
    def __init__(self, instance_type: Type[T]):
        pass

    def __bevy_binder__(self, context) -> Callable[[P], T]:
        """Creates a binder function that will create instances of a type bound to the context."""
