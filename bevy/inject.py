from __future__ import annotations
from bevy.injectable import Injectable
from collections import defaultdict
from sys import modules
import bevy.context


class Inject:
    """Descriptor that is used to inject instances of a type from the owner instance's context."""

    def __init__(self, instance_type):
        self._type = instance_type

    @property
    def type(self):
        return self._type

    def __get__(self, instance: Injectable, owner):
        return instance.__bevy_context__.get_or_create(self.type)


class AnnotationInject(Inject):
    """Descriptor that lazily resolves annotations. This is helpful for avoiding runtime circular imports."""

    def __init__(self, value, scope):
        super().__init__(None)

        self._value = value
        self._scope = scope

    @property
    def type(self):
        if not self._type:
            self._type = self._resolve()

        return super().type

    def _resolve(self):
        return eval(self._value, self._scope)


def injector_factory(annotation, cls: type) -> Inject:
    if isinstance(annotation, str):
        return AnnotationInject(annotation, modules[cls.__module__])

    return Inject(annotation)


class ContextDescriptor:
    def __init__(self):
        self._contexts = defaultdict(bevy.context.Context)

    def __get__(self, instance, owner):
        return self._contexts[instance]


class AutoInject:
    __bevy_context__: bevy.context.Context = ContextDescriptor()


def detect_dependencies(cls):
    """Class decorator that converts annotation attributes into the appropriate Inject/AnnotationInject assignments."""
    for name, value in cls.__annotations__.items():
        setattr(cls, name, injector_factory(value, cls))

    return cls
