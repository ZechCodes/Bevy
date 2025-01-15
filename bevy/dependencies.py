from typing import Any, Callable, overload, TYPE_CHECKING

if TYPE_CHECKING:
    from bevy.containers import Container
    from bevy.factories import Factory


class Dependency:
    def __init__(self, factory: "Callable[[Container], Any] | None" = None):
        self.factory = factory


@overload
def dependency() -> Any:
    ...


@overload
def dependency[T](factory: "Callable[[Container], T] | Factory[None, T]") -> T:
    ...


def dependency[T](factory: "Callable[[Container], T] | Factory[None, T] | None" = None) -> T | Any:
    return Dependency(factory)
