"""The injectable class is used to indicate that Bevy constructors can inject dependencies into the class. It provides a
simple property for fetching the class's dependencies."""
from __future__ import annotations
from inspect import isclass
from typing import Any, Generic, Type, TypeVar, get_type_hints
import bevy


T = TypeVar("T")


class Injectable(Generic[T]):
    """Classes that support the Bevy constructor's dependency injection must inherit from this class."""

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


def is_injectable(obj) -> bool:
    """Determine if an object instance or type supports the Bevy constructor's dependency injection."""
    if isclass(obj):
        return issubclass(obj, Injectable)

    return isinstance(obj, Injectable)
