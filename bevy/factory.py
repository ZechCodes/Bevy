from __future__ import annotations
from typing import Generic, Type, TypeVar
import bevy.context


T = TypeVar("T")


class Factory(Generic[T]):
    def __init__(self, build_type: Type[T], context: bevy.context.Context):
        self.build_type = build_type
        self.context = context

    def __call__(self, *args, **kwargs) -> T:
        return self.context.create(self.build_type, *args, **kwargs)

    def __class_getitem__(cls, build_type: Type[T]) -> FactoryAnnotation:
        return FactoryAnnotation(build_type, cls)


class FactoryAnnotation(Generic[T]):
    def __init__(self, build_type: Type[T], factory: Type[Factory]):
        self.build_type = build_type
        self.factory = factory

    def create_factory(self, context: bevy.context.Context) -> Factory:
        return self.factory(self.build_type, context)
