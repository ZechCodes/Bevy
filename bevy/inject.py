from __future__ import annotations
from bevy.injectable import Injectable
from sys import modules
from typing import Generic, Type, TypeVar
import bevy.context


T = TypeVar("T")


class Inject(Generic[T]):
    """Descriptor that is used to inject instances of a type from the owner instance's context."""

    def __init__(self, instance_type: Type[T]):
        self._type = instance_type

    @property
    def type(self) -> Type[T]:
        return self._type

    def __get__(self, instance: Injectable, owner) -> T:
        return instance.__bevy_context__.get_or_create(self.type, propagate=True)


class AnnotationInject(Inject):
    """Descriptor that lazily resolves annotations. This is helpful for avoiding runtime circular imports."""

    def __init__(self, value, scope):
        super().__init__(None)

        self._value = value
        self._scope = scope

    @property
    def type(self) -> Type[T]:
        if not self._type:
            self._type = self._resolve()

        return super().type

    def _resolve(self) -> Type[T]:
        return eval(self._value, self._scope)


def injector_factory(annotation, cls: Type[T]) -> Inject[T]:
    if isinstance(annotation, str):
        return AnnotationInject(annotation, modules[cls.__module__])

    return Inject(annotation)


class ContextDescriptor:
    def __get__(self, instance, owner) -> bevy.context.Context:
        setattr(instance, "__bevy_context__", bevy.context.Context())
        return instance.__bevy_context__


class AutoInject:
    __bevy_context__: bevy.context.Context = ContextDescriptor()


def detect_dependencies(cls: Type[T]) -> Type[T]:
    """Class decorator that converts annotation attributes into the appropriate Inject/AnnotationInject assignments."""
    for name, value in cls.__annotations__.items():
        setattr(cls, name, injector_factory(value, cls))

    return cls
