from __future__ import annotations
from bevy.factory import FactoryAnnotation
from typing import Any, Dict, Optional, Type, TypeVar, Union
from functools import lru_cache
import sys


T = TypeVar("T")
NO_VALUE = type("NO_VALUE", tuple(), {"__repr__": lambda self: "<NO_VALUE>", "__slots__": []})()


class Context:
    def __init__(self, parent: Context = None):
        self._parent = parent
        self._repository: Dict[Type[T], T] = {}

        self.load(self)

    def branch(self) -> Context:
        """ Creates a new context and adds the current context as its parent. """
        return type(self)(self)

    def create(self, object_type: Type[T], *args, **kwargs) -> T:
        """ Creates an instance of an object using the current context. """
        instance = object_type.__new__(object_type, *args, **kwargs)
        for name, dependency in self._find_dependencies(object_type).items():
            if isinstance(dependency, FactoryAnnotation):
                setattr(instance, name, dependency.create_factory(self))
            else:
                setattr(instance, name, self.get(dependency))
        instance.__init__(*args, **kwargs)
        return instance

    def get(self, object_type: Type[T], *, default: Any = NO_VALUE, propagate: bool = True) -> Optional[T]:
        """ Get's an instance matching the requested type from the context. If default is not set and no match is found
        this will create an instance using the requested type. """
        if self.has(object_type, propagate=False):
            return self._find(object_type)

        if propagate and self._parent:
            return self._parent.get(object_type, default=default)

        if default is NO_VALUE:
            instance = self.create(object_type)
            self.load(instance)
            return instance

        return default

    def has(self, object_type: Type[T], *, propagate: bool = True) -> bool:
        """ Checks if an instance matching the requested type exists in the context or one of its parent contexts. """
        if self._find(object_type) is NO_VALUE:
            return propagate and self._parent and self._parent.has(object_type)
        return True

    def load(self, instance: T) -> Context:
        """ Sets the instance that should be returned when a given type is requested. """
        self._repository[type(instance)] = instance
        return self

    def _find(self, object_type: Type[T]) -> Union[T, NO_VALUE]:
        """ Finds an instance that is either of the requested type or a sub-type of that type. If it is not found
        NO_VALUE will be returned. """
        for repo_type in self._repository:
            if issubclass(repo_type, object_type):
                return self._repository[repo_type]
        return NO_VALUE

    @lru_cache()
    def _find_dependencies(self, object_type: Type) -> Dict[str, Type[T]]:
        dependencies: Dict[str, Type[T]] = {}
        for cls in reversed(object_type.__mro__):
            dependencies.update(
                {
                    name: self._resolve_dependency(cls, annotation_type)
                    for name, annotation_type in getattr(cls, "__annotations__", {}).items()
                    if not hasattr(cls, name)
                }
            )
        return dependencies

    @lru_cache()
    def _resolve_dependency(self, cls: Type, annotation: Union[str, Type]) -> Type:
        if isinstance(annotation, str):
            module = sys.modules[cls.__module__]
            return eval(annotation, module.__dict__)
        return annotation
