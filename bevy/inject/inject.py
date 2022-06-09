from __future__ import annotations
from typing import cast, Generic, overload, Type, TypeVar

from bevy.inject.annotations import AnnotationGetter
from bevy.inject.context_injector import ContextInjector
from bevy.inject.inject_strategies import (
    InjectionStrategy,
    InjectAllStrategy,
    InjectAllowStrategy,
    InjectDisallowStrategy,
)


T = TypeVar("T")


class Inject:
    ALL = InjectAllStrategy()
    ONLY = InjectAllowStrategy
    IGNORE = InjectDisallowStrategy


class Bevy:
    __bevy_context__ = None
    bevy = ContextInjector()

    def __init_subclass__(cls, *, inject: InjectionStrategy | None = None, **kwargs):
        strategy = inject or InjectAllowStrategy()
        dependencies = strategy.get_declared_dependencies(cls)
        strategy.create_injectors(cls, dependencies)

    def __class_getitem__(cls, strategy: InjectionStrategy) -> Type[Bevy]:
        return cast(
            Type[Bevy], type(cls.__name__, (cls,), {"_detection_strategy": strategy})
        )


class InjectionDescriptor(Generic[T]):
    def __init__(
        self,
        on_cls: Type[Bevy],
        attr_name: str,
        annotation_getter: AnnotationGetter[Type[T], T],
    ):
        self.on_cls = on_cls
        self.attr_name = attr_name
        self.annotation_getter = annotation_getter

    @overload
    def __get__(self, instance: Bevy, owner) -> T:
        ...

    @overload
    def __get__(self, instance: None, owner) -> InjectionDescriptor:
        ...

    def __get__(self, instance: Bevy | None, owner) -> T | InjectionDescriptor:
        if not instance:
            return self

        type_hint = self.annotation_getter.get()
        return instance.bevy.get(type_hint) or instance.bevy.create(
            type_hint, add_to_context=True
        )
