import sys
import dataclasses
from inspect import get_annotations
from typing import Any, Generic, Type, TypeVar

from bevy.options import Option, Value, Null
from bevy.repository import get_repository

_K = TypeVar("_K")


class LazyAnnotationResolver:
    def __init__(self, annotation, cls):
        self.annotation = annotation
        self.cls = cls
        self._resolved_type = Null() if isinstance(annotation, str) else Value(annotation)

    @property
    def resolved_type(self) -> Option[Type]:
        match self._resolved_type:
            case Value() as resolved_type:
                return resolved_type

            case Null():
                resolved_type = self._resolve()
                self._resolved_type = Value(resolved_type)
                return self._resolved_type

    def _resolve(self):
        ns = _get_class_namespace(self.cls)
        return ns[self.annotation]


class Dependency(Generic[_K]):
    """This class can be used to indicate fields that need to be injected. It also acts as a descriptor that can
    discover the key that needs to be injected and handle injecting the corresponding instance for that key when
    accessed.

    To avoid typing errors that may arise from assigning instances of `Dependency` to fields, use the `dependency`
    function. That function returns a new instance of `Dependency` but has a return type of `typing.Any`.
    """

    def __init__(self):
        self._key_resolver: LazyAnnotationResolver | None = LazyAnnotationResolver(None, None)

    def __get__(self, instance: object, owner: Type):
        if instance is None:
            if hasattr(owner, dataclasses._PARAMS):
                return dataclasses.field(default_factory=self._inject_dependency)

            return self

        return self._inject_dependency()

    def __set_name__(self, owner: Type, name: str):
        annotations = get_annotations(owner)
        self._key_resolver = LazyAnnotationResolver(annotations[name], owner)

    def _inject_dependency(self):
        match self._key_resolver.resolved_type:
            case Value(key):
                repo = get_repository()
                return repo.get(key)

            case Null():
                raise Exception("The dependency has not been setup")


def dependency() -> Any:
    """This helper function allows instances of the `Dependency` type to be assigned to fields without breaking type
    checking."""
    return Dependency()


def _get_class_namespace(cls: Type) -> dict[str, Any]:
    """Attempts to get the global variables in the module that a class was declared in."""
    try:
        return vars(sys.modules[cls.__module__])
    except KeyError:
        return {}
