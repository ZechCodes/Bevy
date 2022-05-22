from __future__ import annotations
from functools import cache, wraps
from typing import Generic, overload, Type, TypeVar
from inspect import get_annotations

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


class Dependencies:
    __bevy__ = ContextInjector()

    def __init_subclass__(cls, **kwargs):
        _try_early_injector_creation(cls)


class Inject(Generic[T]):
    def __init__(self, type_: Type[T]):
        self.type = type_

    @overload
    def __get__(self, instance: Dependencies, owner) -> T:
        ...

    @overload
    def __get__(self, instance: None, owner) -> Inject:
        ...

    def __get__(self, instance: Dependencies | None, owner) -> T | Inject:
        if not instance:
            return self

        return instance.__bevy__.get(self.type)

    def __class_getitem__(cls, item):
        return Inject(item)


def _try_early_injector_creation(cls):
    try:
        _build_injectors(cls)
    except Exception:
        _inject_deferred_injector_builder(cls)


def _inject_deferred_injector_builder(cls):
    init = cls.__init__

    @wraps(init)
    def new_init(*args):
        _build_injectors(cls)
        cls.__init__ = init
        cls.__init__(*args)

    cls.__init__ = new_init


def _build_injectors(cls):
    for name, annotation in get_annotations(cls, eval_str=True).items():
        if isinstance(annotation, Inject):
            setattr(cls, name, annotation)
