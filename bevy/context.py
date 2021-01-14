from __future__ import annotations
from abc import ABC, abstractmethod
from bevy.factory import FactoryAnnotation
from typing import Any, Dict, Optional, Type, TypeVar, Union
from functools import lru_cache
import bevy.injectable
import sys


T = TypeVar("T")
NO_VALUE = type(
    "NO_VALUE", tuple(), {"__repr__": lambda self: "<NO_VALUE>", "__slots__": []}
)()


class BaseContext(ABC):
    """The base context provides the core logic for all context types.

    Contexts are used as a factory for creating instances of classes that have their required dependencies injected. The
    context then stores the instances used to fulfill the requirements in a repository so they can be used again if any
    other class instance requires them. This allows all instance created by an instance to share the same dependencies.

    Contexts also allows for pre-initialized instances to be added to the repository which will later be used to fulfill
    dependency requirements. This allows for more complex initialization of dependencies, such as for connecting to a
    database.

    Additionally each context has the ability to branch off sub-contexts. The context will share its dependency
    repository with the sub-contexts but any new dependencies created by the sub-contexts will not be propagated back.
    This allows for isolating objects that may have similar dependency requirements but that should have distinct
    dependency instances.

    The context can inject itself as a dependency if a class requires the BaseContext. It's not recommended to require
    the Context or GreedyContext classes as they would fail to inject if the other type of context is used."""

    def __init__(self, parent: BaseContext = None):
        self._parent = parent
        self._repository: Dict[Type[T], T] = {}

        self.add(self)

    def add(self, instance: T) -> BaseContext:
        """ Adds a pre-initialized instance to the context's repository. """
        self._repository[type(instance)] = instance
        return self

    def branch(self) -> BaseContext:
        """Creates a new context and adds the current context as its parent. The new context will have access to the
        repository of the branched context, new dependencies that it creates will not be propagated. This is useful for
        isolating instances that may have similar dependencies but that should have distinct dependency instances."""
        return type(self)(self)

    @abstractmethod
    def create(self, object_type: Type[T], *args, **kwargs) -> T:
        """Creates an instance of an object using the current context's repository to fulfill all required
        dependencies. For any dependencies not found in the repository the context will attempt to initialize them
        without any arguments."""
        ...

    def get(
        self, object_type: Type[T], *, default: Any = NO_VALUE, propagate: bool = True
    ) -> Optional[T]:
        """Get's an instance matching the requested type from the context. If default is not set and no match is found
        this will attempt to create an instance by calling the requested type with no arguments. The returned instance
        maybe a subclass of the type but it will never be a superclass. If propagation is allowed and no match is found
        it will attempt to find a match by propagating up through the parent contexts.
        """
        if self.has(object_type, propagate=False):
            return self._find(object_type)

        if propagate and self._parent and self._parent.has(object_type):
            return self._parent.get(object_type, default=default)

        if default is NO_VALUE:
            instance = self.create(object_type)
            self.add(instance)
            return instance

        return default

    def has(self, object_type: Type[T], *, propagate: bool = True) -> bool:
        """ Checks if an instance matching the requested type exists in the context or one of its parent contexts. """
        if self._find(object_type) is NO_VALUE:
            return propagate and self._parent and self._parent.has(object_type)
        return True

    def _find(self, object_type: Type[T]) -> Union[T, NO_VALUE]:
        """Finds an instance that is either of the requested type or a sub-type of that type. If it is not found
        NO_VALUE will be returned."""
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
                    for name, annotation_type in getattr(
                        cls, "__annotations__", {}
                    ).items()
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


class GreedyContext(BaseContext):
    """ The Greedy Context will attempt to inject dependencies for any object regardless of type. """

    def create(self, object_type: Type[T], *args, **kwargs) -> T:
        """Creates an instance of an object using the current context's repository to fulfill all required
        dependencies. For any dependencies not found in the repository the context will attempt to initialize them
        without any arguments."""
        instance = object_type.__new__(object_type, *args, **kwargs)
        for name, dependency in self._find_dependencies(object_type).items():
            if isinstance(dependency, FactoryAnnotation):
                setattr(instance, name, dependency.create_factory(self))
            else:
                setattr(instance, name, self.get(dependency))
        instance.__init__(*args, **kwargs)
        return instance


class Context(GreedyContext):
    """ Context will only attempt to inject dependencies on subclasses of bevy.Injectable. """

    def create(self, object_type: Type[T], *args, **kwargs) -> T:
        """Creates an instance of an object using the current context's repository to fulfill all required
        dependencies. For any dependencies not found in the repository the context will attempt to initialize them
        without any arguments."""
        if not issubclass(object_type, bevy.Injectable):
            return object_type(*args, **kwargs)

        return super().create(object_type, *args, **kwargs)
