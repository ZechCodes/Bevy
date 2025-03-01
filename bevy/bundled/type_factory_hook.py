from typing import Type

from tramp.optionals import Optional

from bevy.containers import Container
from bevy.hooks import hooks


@hooks.HANDLE_UNSUPPORTED_DEPENDENCY
def type_factory[T](container: Container, dependency: Type[T]) -> Optional[T]:
    """This hook adds a dependency factory that injects an instances of the dependency type."""
    if isinstance(dependency, type):
        return Optional.Some(container.call(dependency))

    return Optional.Nothing()
