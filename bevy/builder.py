from functools import partial
from typing import Generic, Type, TypeVar


T = TypeVar("T")


class Builder(Generic[T]):
    def __init__(self, instance_type: Type[T]):
        self._type = instance_type

    def __call__(self, builder, *args, **kwargs) -> T:
        return builder(*args, **kwargs)

    def __bevy_create__(self, context):
        return partial(self, context.bind(self._type))

    def __class_getitem__(cls, item):
        return cls(item)
