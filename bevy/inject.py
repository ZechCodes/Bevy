from __future__ import annotations
from functools import cache, wraps
from typing import Annotated, Generic, overload, Type, TypeVar, get_type_hints, get_args, get_origin

import bevy.context as context

T = TypeVar("T")


class ContextAlreadySet(RuntimeError): ...


class ContextAccessor:
    def __init__(self):
        self._context: context.Context | None = None

    @property
    def context(self) -> context.Context:
        if not self._context:
            self._context = context.Context()

        return self._context

    @context.setter
    def context(self, value):
        if self._context:
            raise ContextAlreadySet(f"The context has already been set on {self}")

        self._context = value

    def get(self, type_: Type[T], *args, **kwargs) -> T:
        provider = self.context.get_provider_for(type_)
        return provider.get_instance(*args, **kwargs)


class ContextInjector:
    @overload
    def __get__(self, instance: None, owner: Type[T]) -> None:
        ...

    @overload
    def __get__(self, instance: T, owner: Type[T]) -> ContextAccessor:
        ...

    @cache
    def __get__(self, instance: T | None, owner: Type[T]) -> ContextAccessor | None:
        if instance:
            return ContextAccessor()

    def __set__(self, instance, value):
        instance.__bevy__.context = value


class Dependencies(Generic[T]):
    __bevy__ = ContextInjector()

    def __init_subclass__(cls, **kwargs):
        init = cls.__init__

        @wraps(init)
        def new_init(*args):
            _build_injectors(cls)
            cls.__init__ = init
            cls.__init__(*args)

        cls.__init__ = new_init


class Inject(Generic[T]):
    def __init__(self, type_: Type[T]):
        self.type = type_

    def __get__(self, instance: Dependencies, owner) -> T:
        return instance.__bevy__.get(self.type)

    def __class_getitem__(cls, item):
        return Inject(item)


def _build_injectors(cls):
    for name, annotation in get_type_hints(cls).items():
        if isinstance(annotation, Inject):
            setattr(cls, name, annotation)
