from collections.abc import Callable
from functools import update_wrapper
from typing import overload, Sequence, Type

import bevy.registries as r


class Factory[**P, T]:
    """A wrapper for dependency factories. This makes it easier to define factories that can handle various types and
    add them to the registry."""
    def __init__(self, dependency_types: Sequence[Type[T]], factory: "r.DependencyFactory[P, T]"):
        self.dependency_types = dependency_types
        self.factory = factory

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.factory(*args, **kwargs)

    @overload
    def register_factory(self):
        ...

    @overload
    def register_factory(self, registry: "r.Registry | None"):
        ...

    def register_factory(self, registry: "r.Registry | None" = None):
        """Adds the factory to the registry for each dependency type the factory supports. If the registry is not
        provided or is None the global registry will be used."""
        registry = r.get_registry(registry)
        for dependency_type in self.dependency_types:
            registry.add_factory(self, dependency_type)


def factory[**P, T](*dependency_types: Type[T]) -> "Callable[[r.DependencyFactory[P, T]], r.DependencyFactory[P, T]]":
    """Decorator that wraps a factory function in a factory wrapper."""
    def decorator(dependency_factory: Factory[P, T]) -> r.DependencyFactory[P, T]:
        wrapper = Factory[P, T](dependency_types, dependency_factory)
        wrapper = update_wrapper(wrapper, dependency_factory)
        return wrapper

    return decorator


def create_type_factory[T](dependency_type: Type[T], *args, **kwargs) -> Factory[None, T]:
    """Creates a factory for a type that can be added to a registry. It takes the type and any arguments that should be
    passed to the type constructor."""
    return Factory([dependency_type], lambda _: dependency_type(*args, **kwargs))
