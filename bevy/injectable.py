"""The injectable class is used to indicate that Bevy constructors can inject dependencies into the class. It provides a
simple property for fetching the class's dependencies."""
from __future__ import annotations
from functools import wraps
from typing import (
    Any,
    Optional,
    Protocol,
    Type,
    TypeVar,
    get_type_hints,
    runtime_checkable,
)
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
        ...

    @classmethod
    @property
    def __bevy_dependencies__(cls) -> dict[str, Any]:
        """Dictionary of attribute names and their desired dependency type."""
        ...


class BaseInjectableImplementation:
    @classmethod
    def __bevy_construct__(
        cls: Type[T], instance: T, constructor: bevy.Constructor, *args, **kwargs
    ) -> T:
        for name, dependency in cls.__bevy_dependencies__.items():
            constructor.inject(dependency, instance, name)
        return instance

    @classmethod
    @property
    def __bevy_dependencies__(cls) -> dict[str, Any]:
        """Dictionary of attribute names and their desired dependency type."""
        return get_type_hints(cls)


def injectable(cls: Type[T]) -> Type[Injectable[T]]:
    """Decorator to make a class compatible with the Injectable protocol and implement the necessary injection logic."""

    @wraps(cls.__new__)
    def new(*args, bevy_constructor: Optional[bevy.Constructor] = None, **kwargs):
        if not bevy_constructor:
            return bevy.Constructor(custom_class).build()

        inst = cls.__new__(*args, **kwargs)
        custom_class.__bevy_construct__(inst, bevy_constructor, *args, **kwargs)
        return inst

    bases = list(cls.__bases__)
    if object in bases:
        bases.remove(object)

    custom_class: Type[Injectable[T]] = type(
        cls.__name__,
        (cls, *bases, BaseInjectableImplementation),
        {"__new__": new, "__module__": cls.__module__},
    )

    return custom_class


def is_injectable(obj) -> bool:
    """Determine if an object instance or type supports the Bevy constructor's dependency injection."""
    return isinstance(obj, Injectable)
