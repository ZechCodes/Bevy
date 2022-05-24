from __future__ import annotations
from functools import wraps
from typing import (
    Generic,
    Type,
    TypeVar,
    get_type_hints,
)

import bevy.context as context

T = TypeVar("T")


class Dependencies(Generic[T]):
    __bevy__: context.Context | None = None

    def __init_subclass__(cls, **kwargs):
        init = cls.__init__

        @wraps(init)
        def new_init(*args):
            _build_injectors(cls)
            cls.__init__ = init
            cls.__init__(*args)

        cls.__init__ = new_init

    def __init__(self, *args, **kwargs):
        self.__bevy__ = self.__bevy__ or context.Context()


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
