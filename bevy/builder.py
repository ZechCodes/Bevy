"""The builder protocol should be used by classes that are used to construct objects."""
from __future__ import annotations
from typing import Protocol, Type, TypeVar, runtime_checkable
import bevy


T = TypeVar("T")


@runtime_checkable
class Builder(Protocol[T]):
    """The builder protocol should be implemented by any class that needs the context to build instances of a
    class."""

    @classmethod
    def __bevy_build__(cls: Type[T], bevy_context: bevy.Context, *args, **kwargs) -> T:
        ...


def is_builder(obj) -> bool:
    """Determine if an object instance or type implements the builder protocol."""
    return isinstance(obj, Builder)
