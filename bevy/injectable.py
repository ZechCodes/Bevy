"""The injectable class is used to indicate that Bevy contexts can inject dependencies into the class. It provides a
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
    def __bevy_construct__(cls: Type[T], context: bevy.Context, *args, **kwargs) -> T:
        ...

    @classmethod
    @property
    def __bevy_dependencies__(cls) -> dict[str, Any]:
        """Dictionary of attribute names and their desired dependency type."""
        ...


def injectable(cls: Type[T]) -> Injectable[Type[T]]:
    """Decorator to make a class compatible with the Injectable protocol and implement the necessary injection logic.

    The goal is to add injection logic to the classes without changing how classes function. It shouldn't be possible
    for someone to unintentionally break the injection system by adding a dunder init/new/etc. method of their own. It
    also means that no Bevy args should be required when writing standard methods like dunder init and dunder new.

    This decorator accomplishes that by creating a new class object that mimics the decorated class. It uses the same
    attributes, bases, and name. It then overrides the dunder new and dunder init methods. The dunder new handles
    calling the Bevy construction code, it then removes the Bevy args and calls the original implementation of dunder
    new. Similarly the dunder init removes the Bevy args and calls the original implementation.
    """

    old_new = cls.__new__

    @wraps(old_new)
    def new(cls_, *args, **kwargs):
        context = kwargs.pop("__bevy_context__", None) or bevy.Context(cls_)
        inst = (
            old_new(cls_)
            if old_new.__self__ is object
            else old_new(cls_, *args, **kwargs)
        )
        cls_.__bevy_construct__(inst, context, *args, **kwargs)
        return inst

    cls.__new__ = new

    old_init = cls.__init__

    @wraps(old_init)
    def init(self_, *args, **kwargs):
        kwargs.pop("__bevy_context__", None)
        old_init(self_, *args, **kwargs)

    cls.__init__ = init

    if not hasattr(cls, "__bevy_construct__"):

        @classmethod
        def __bevy_construct__(
            cls: Type[T], instance: T, context: bevy.Context, *args, **kwargs
        ) -> T:
            for name, dependency in cls.__bevy_dependencies__.items():
                context.inject(dependency, instance, name)
            return instance

        cls.__bevy_construct__ = __bevy_construct__

    if not hasattr(cls, "__bevy_dependencies__"):

        @classmethod
        @property
        def __bevy_dependencies__(cls) -> dict[str, Any]:
            """Dictionary of attribute names and their desired dependency type."""
            return get_dependencies(cls)

        cls.__bevy_dependencies__ = __bevy_dependencies__

    return cls


def get_dependencies(cls):
    """Gets the type annotations which should be used as the class dependencies. This will include all annotations names
    that haven't been assigned to."""
    return {
        name: annotation
        for name, annotation in get_type_hints(cls).items()
        if not hasattr(cls, name)
    }


def is_injectable(obj) -> bool:
    """Determine if an object instance or type supports the Bevy context's dependency injection."""
    return isinstance(obj, Injectable)
