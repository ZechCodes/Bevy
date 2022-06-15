from __future__ import annotations
from abc import ABC, abstractmethod
from inspect import get_annotations
from typing import Type


from bevy.inject.annotations import AnnotationGetter
import bevy.inject.inject as i


def is_inject(obj) -> bool:
    return (
        obj is i.Inject
        or isinstance(obj, i.Inject)
        or (isinstance(obj, type) and issubclass(obj, i.Inject))
    )


class InjectionStrategy(ABC):
    @abstractmethod
    def get_declared_dependencies(self, t: type) -> dict[str, AnnotationGetter]:
        ...

    def create_injectors(
        self, on_cls: Type[i.Bevy], dependencies: dict[str, AnnotationGetter]
    ):
        for name, annotation_getter in dependencies.items():
            setattr(
                on_cls, name, i.InjectionDescriptor(on_cls, name, annotation_getter)
            )


class InjectAllStrategy(InjectionStrategy):
    """This will scan a class's attribute annotations and create injection descriptors for any that aren't already
    assigned."""

    def get_declared_dependencies(self, t: type) -> dict[str, AnnotationGetter]:
        return {
            name: AnnotationGetter.factory(t, name, annotation, value)
            for name, annotation in get_annotations(t).items()
            if ((value := getattr(t, name, None)) is None or is_inject(value))
        }


class InjectAllowStrategy(InjectionStrategy):
    """This will scan a class's attribute annotations and create injection descriptors for any that aren't already
    assigned and that are in the allowed set."""

    def __init__(self, *allow: str):
        super().__init__()
        self.allow = set(allow)

    def get_declared_dependencies(self, t: type) -> dict[str, AnnotationGetter]:
        return {
            name: AnnotationGetter.factory(t, name, annotation, value)
            for name, annotation in get_annotations(t).items()
            if (
                (value := getattr(t, name, None)) is None
                and name in self.allow
                or is_inject(value)
            )
        }


class InjectDisallowStrategy(InjectionStrategy):
    """This will scan a class's attribute annotations and create injection descriptors for any that aren't already
    assigned and that aren't in the disallowed set."""

    def __init__(self, *disallow: str):
        super().__init__()
        self.disallow = set(disallow)

    def get_declared_dependencies(self, t: type) -> dict[str, AnnotationGetter]:
        return {
            name: AnnotationGetter.factory(t, name, annotation, value)
            for name, annotation in get_annotations(t).items()
            if (
                (value := getattr(t, name, None)) is None
                and name not in self.disallow
                or is_inject(value)
            )
        }