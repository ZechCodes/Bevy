from __future__ import annotations
from functools import cache
from typing import Any, Generic, get_type_hints, TypeVar

import bevy.inject.inject as i


AnnotationType = TypeVar("AnnotationType", bound=type)
T = TypeVar("T")


class AnnotationGetter(Generic[AnnotationType, T]):
    def __init__(self, owner_cls: type, attr_name: str, annotation: AnnotationType[T], value: i.Inject | None):
        self.annotation = annotation
        self.attr_name = attr_name
        self.owner_cls = owner_cls
        self.value = value

    def get(self) -> AnnotationType[T]:
        return self.annotation

    @classmethod
    def factory(cls, owner_cls: type, attr_name: str, annotation: Any, value: i.Inject | None) -> AnnotationGetter:
        if isinstance(annotation, str):
            return LazyAnnotationGetter(owner_cls, attr_name, annotation, value)

        return AnnotationGetter(owner_cls, attr_name, annotation, value)


class LazyAnnotationGetter(AnnotationGetter):
    def __init__(self, owner_cls: type, attr_name: str, annotation: str, value: i.Inject | None):
        super().__init__(owner_cls, attr_name, annotation, value)

    @cache
    def get(self) -> type:
        type_hints = get_type_hints(self.owner_cls)
        return type_hints[self.attr_name]