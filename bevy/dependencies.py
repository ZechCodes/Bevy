from typing import Any, Callable, overload, TYPE_CHECKING

if TYPE_CHECKING:
    from bevy.containers import Container
    from bevy.factories import Factory


class DependencyMetadata:
    """Dependency metadata wrapper. A factory function can be provided for creating the dependency, this factory
    function must take a container instance as a parameter."""
    def __init__(self, factory: "Callable[[Container], Any] | None" = None):
        self.factory = factory


@overload
def dependency() -> Any:
    ...


@overload
def dependency[T](factory: "Callable[[Container], T] | Factory[None, T]") -> T:
    ...


def dependency[T](factory: "Callable[[Container], T] | Factory[None, T] | None" = None) -> T | Any:
    """Intended to be called as a parameter default value. It assigns the default to a dependency metadata object. A
    factory function can be passed that returns an instance of the dependency type."""
    return DependencyMetadata(factory)
