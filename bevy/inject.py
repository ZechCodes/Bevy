from __future__ import annotations

import abc
from functools import cache
from typing import Any, cast, Generic, overload, Type, TypeVar, get_type_hints
from inspect import get_annotations

import bevy.context as context
import bevy.base_context as base_context

T = TypeVar("T")
AnnotationType = TypeVar("AnnotationType", bound=type)


class ContextInjector:
    @overload
    def __get__(self, instance: None, owner: Type[T]) -> None:
        ...

    @overload
    def __get__(self, instance: T, owner: Type[T]) -> base_context.BaseContext:
        ...

    @cache
    def __get__(self, instance: T | None, owner: Type[T]) -> base_context.BaseContext | None:
        if not instance:
            return

        if instance.__bevy_context__:
            return instance.__bevy_context__

        return context.Context()


class AnnotationGetter(Generic[AnnotationType, T]):
    def __init__(self, owner_cls: type, attr_name: str, annotation: AnnotationType[T], value: Inject | None):
        self.annotation = annotation
        self.attr_name = attr_name
        self.owner_cls = owner_cls
        self.value = value

    def get(self) -> AnnotationType[T]:
        return self.annotation

    @classmethod
    def factory(cls, owner_cls: type, attr_name: str, annotation: Any, value: Inject | None) -> AnnotationGetter:
        if isinstance(annotation, str):
            return LazyAnnotationGetter(owner_cls, attr_name, annotation, value)

        return AnnotationGetter(owner_cls, attr_name, annotation, value)


class LazyAnnotationGetter(AnnotationGetter):
    def __init__(self, owner_cls: type, attr_name: str, annotation: str, value: Inject | None):
        super().__init__(owner_cls, attr_name, annotation, value)

    @cache
    def get(self) -> type:
        type_hints = get_type_hints(self.owner_cls)
        return type_hints[self.attr_name]


class InjectionStrategy(abc.ABC):
    @abc.abstractmethod
    def get_declared_dependencies(self, t: type) -> dict[str, AnnotationGetter]:
        ...

    def create_injectors(self, on_cls: Type[BevyInject], dependencies: dict[str, AnnotationGetter]):
        for name, annotation_getter in dependencies.items():
            setattr(on_cls, name, InjectionDescriptor(on_cls, name, annotation_getter))


class InjectAllStrategy(InjectionStrategy):
    """ This will scan a class's attribute annotations and create injection descriptors for any that aren't already
    assigned. """
    def get_declared_dependencies(self, t: type) -> dict[str, AnnotationGetter]:
        return {
            name: AnnotationGetter.factory(t, name, annotation, value)
            for name, annotation in get_annotations(t).items()
            if (value := getattr(t, name, None)) is None or isinstance(value, Inject)
        }


class InjectAllowedStrategy(InjectionStrategy):
    """ This will scan a class's attribute annotations and create injection descriptors for any that aren't already
    assigned and that are in the allowed set. """
    def __init__(self, allow: set[str] | None = None):
        super().__init__()
        self.allow = allow or set()

    def __class_getitem__(cls, allowed: tuple[str]) -> InjectAllowedStrategy:
        return InjectAllowedStrategy(_make_set(allowed))

    def get_declared_dependencies(self, t: type) -> dict[str, AnnotationGetter]:
        return {
            name: AnnotationGetter.factory(t, name, annotation, value)
            for name, annotation in get_annotations(t).items()
            if (value := getattr(t, name, None)) is None and name in self.allow or isinstance(value, Inject)
        }


class InjectDisallowedStrategy(InjectionStrategy):
    """ This will scan a class's attribute annotations and create injection descriptors for any that aren't already
    assigned and that aren't in the disallowed set. """
    def __init__(self, disallow: set[str]):
        super().__init__()
        self.disallow = disallow

    def __class_getitem__(cls, disallow: tuple[str]) -> InjectDisallowedStrategy:
        return InjectDisallowedStrategy(_make_set(disallow))

    def get_declared_dependencies(self, t: type) -> dict[str, AnnotationGetter]:
        return {
            name: AnnotationGetter.factory(t, name, annotation, value)
            for name, annotation in get_annotations(t).items()
            if (value := getattr(t, name, None)) is None and name not in self.disallow or isinstance(value, Inject)
        }


class Detect:
    ALL = InjectAllStrategy()
    ONLY = InjectAllowedStrategy
    IGNORE = InjectDisallowedStrategy


class BevyInject:
    __bevy_context__ = None
    _detection_strategy = Detect.ONLY()
    bevy = ContextInjector()

    def __init_subclass__(cls, **kwargs):
        dependencies = cls._detection_strategy.get_declared_dependencies(cls)
        cls._detection_strategy.create_injectors(cls, dependencies)

    def __class_getitem__(cls, strategy: InjectionStrategy) -> Type[BevyInject]:
        return cast(
            Type[BevyInject],
            type(
                cls.__name__,
                (cls,),
                {
                    "_detection_strategy": strategy
                }
            )
        )


class Inject:
    ...


class InjectionDescriptor(Generic[T]):
    def __init__(self, on_cls: Type[BevyInject], attr_name: str, annotation_getter: AnnotationGetter[Type[T], T]):
        self.on_cls = on_cls
        self.attr_name = attr_name
        self.annotation_getter = annotation_getter

    @overload
    def __get__(self, instance: BevyInject, owner) -> T:
        ...

    @overload
    def __get__(self, instance: None, owner) -> InjectionDescriptor:
        ...

    def __get__(self, instance: BevyInject | None, owner) -> T | InjectionDescriptor:
        if not instance:
            return self

        type_hint = self.annotation_getter.get()
        return instance.bevy.get(type_hint) or instance.bevy.create(type_hint, add_to_context=True)


def _make_set(item) -> set:
    if isinstance(item, tuple):
        return set(item)

    return {item}
