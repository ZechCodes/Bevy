from __future__ import annotations
from bevy.context import Context
from bevy.inject import Injector
from typing import Callable, Generic, Type, TypeVar


T = TypeVar("T")
MAKE_TYPE = TypeVar("MAKE_TYPE")


class Factory(Injector, Generic[MAKE_TYPE]):
    def __init__(self, make_type: Type[MAKE_TYPE]):
        super().__init__()
        self._make_type = make_type

    def __class_getitem__(cls, make_type: Type[MAKE_TYPE]) -> Factory[MAKE_TYPE]:
        return Factory(make_type)

    def __bevy_inject__(
        self, instance: T, context: Context
    ) -> Callable[..., MAKE_TYPE]:
        def build(*args, **kwargs) -> MAKE_TYPE:
            return context.build(self._make_type, *args, **kwargs)

        return build
