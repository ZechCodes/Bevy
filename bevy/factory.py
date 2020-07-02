import bevy
import bevy.context
from typing import Generic, Type, TypeVar


T = TypeVar("T")


class Factory(Generic[T]):
    def __init__(self, build_type: T, context: bevy.context.Context):
        self._builder = bevy.bevy.BevyMeta.builder(build_type, context=context)

    def __call__(self, *args, **kwargs) -> T:
        return self._builder.build(*args, **kwargs)

    def __class_getitem__(cls, build_type: T):
        return FactoryAnnotation(build_type, cls)


class FactoryAnnotation(Generic[T]):
    def __init__(self, build_type: T, factory: Type[Factory]):
        self.build_type = build_type
        self.factory = factory

    def create_factory(self, context: bevy.context.Context) -> Factory:
        return self.factory(self.build_type, context)
