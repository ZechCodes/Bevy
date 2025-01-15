from collections.abc import Callable
from functools import update_wrapper
from typing import Sequence, Type
import bevy.registries as r


class Factory[**P, T]:
    def __init__(self, dependency_types: Sequence[Type[T]], factory: "r.DependencyFactory[P, T]"):
        self.dependency_types = dependency_types
        self.factory = factory

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.factory(*args, **kwargs)

    def register_factory(self, registry: "r.Registry | None" = None):
        registry = r.get_registry(registry)
        for dependency_type in self.dependency_types:
            registry.add_factory(self, dependency_type)


def factory[**P, T](*dependency_types: Type[T]) -> "Callable[[r.DependencyFactory[P, T]], r.DependencyFactory[P, T]]":
    def decorator(dependency_factory: Factory[P, T]) -> r.DependencyFactory[P, T]:
        wrapper = Factory[P, T](dependency_types, dependency_factory)
        wrapper = update_wrapper(wrapper, dependency_factory)
        return wrapper

    return decorator


def create_type_factory[T](dependency_type: Type[T], *args, **kwargs) -> Factory[None, T]:
    return Factory([dependency_type], lambda _: dependency_type(*args, **kwargs))
