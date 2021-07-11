"""The injectable class is used to indicate that Bevy constructors can inject dependencies into the class. It provides a
simple property for fetching the class's dependencies."""
from __future__ import annotations
from typing import Any, Protocol, Type, TypeVar, get_type_hints, runtime_checkable
import bevy


T = TypeVar("T")


@runtime_checkable
class Injectable(Protocol[T]):
    """The injectable protocol should be implemented by any class that needs to have their dependencies injected. Any
    class can be made to support this protocol by using the injectable decorator."""

    @classmethod
    def __bevy_construct__(
        cls: Type[T], constructor: bevy.Constructor, *args, **kwargs
    ) -> T:
        inst = cls.__new__(cls, *args, **kwargs)
        for name, dependency in cls.__bevy_dependencies__.items():
            constructor.inject(dependency, inst, name)
        inst.__init__(*args, **kwargs)
        return inst

    @classmethod
    @property
    def __bevy_dependencies__(cls) -> dict[str, Any]:
        """Dictionary of attribute names and their desired dependency type."""
        return get_type_hints(cls)


def injectable(cls: Type[T]) -> Type[Injectable[T]]:
    """Decorator to make a class compatible with the Injectable protocol. This is unnecessary if the class provides it's
    own implementations of the __bevy_construct__ and __bevy_dependencies__ methods."""
    if not hasattr(cls, "__bevy_construct__"):
        cls.__bevy_construct__ = classmethod(Injectable.__bevy_construct__.__func__)

    if not hasattr(cls, "__bevy_dependencies__"):
        cls.__bevy_dependencies__ = classmethod(
            Injectable.__dict__["__bevy_dependencies__"].__func__
        )

    return cls


def is_injectable(obj) -> bool:
    """Determine if an object instance or type supports the Bevy constructor's dependency injection."""
    return isinstance(obj, Injectable)
