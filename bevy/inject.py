from __future__ import annotations
from functools import wraps
from typing import Generic, overload, Type, TypeVar
from inspect import get_annotations

import bevy.context as context


T = TypeVar("T")


class Dependencies:
    __bevy__: context.Context | None = None

    def __init_subclass__(cls, **kwargs):
        try:
            _setup_class(cls)
        except Exception:
            _defer_class_setup(cls)

    def __init__(self, *args, **kwargs):
        self.__bevy_init__(*args, **kwargs)

    def __bevy_init__(self, *args, **kwargs):
        self.__bevy__ = context.Context()


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


def _defer_class_setup(cls):
    init = cls.__init__

    @wraps(init)
    def new_init(*args, **kwargs):
        _setup_class(cls)
        cls.__init__ = init
        cls.__init__(*args, **kwargs)

    cls.__init__ = new_init


def _setup_class(cls):
    for name, annotation in get_annotations(cls, eval_str=True).items():
        if isinstance(annotation, Inject):
            setattr(cls, name, annotation)
