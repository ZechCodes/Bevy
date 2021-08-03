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
    """Decorator to make a class compatible with the Injectable protocol and implement the necessary injection logic.

    The goal is to add injection logic to the classes without changing how classes function. It shouldn't be possible
    for someone to unintentionally break the injection system by adding a dunder init/new/etc. method of their own. It
    also means that no Bevy args should be required when writing standard methods like dunder init and dunder new.

    This decorator accomplishes that by creating a new class object that mimics the decorated class. It uses the same
    attributes, bases, and name. It then overrides the dunder new and dunder init methods. The dunder new handles
    calling the Bevy construction code, it then removes the Bevy args and calls the original implementation of dunder
    new. Similarly the dunder init removes the Bevy args and calls the original implementation.
    """

    @wraps(cls.__new__)
    def new(cls_, *args, **kwargs):
        constructor = kwargs.pop("__bevy_constructor__", None) or bevy.Constructor(cls_)
        inst = cls.__new__(cls_, *args, **kwargs)
        cls_.__bevy_construct__(inst, constructor, *args, **kwargs)
        return inst

    @wraps(cls.__init__)
    def init(self_, *args, **kwargs):
        kwargs.pop("__bevy_constructor__", None)
        cls.__init__(self_, *args, **kwargs)

    attrs = dict(vars(cls))
    attrs["__new__"] = new
    attrs["__init__"] = init

    bases = list(cls.__bases__)
    if object in bases:
        bases.remove(object)
    bases.append(BaseInjectableImplementation)

    return type(cls.__name__, tuple(bases), attrs)


def is_injectable(obj) -> bool:
    """Determine if an object instance or type supports the Bevy constructor's dependency injection."""
    return isinstance(obj, Injectable)
