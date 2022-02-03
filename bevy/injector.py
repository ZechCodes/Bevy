from typing import Protocol, TypeVar


T = TypeVar("T")


class Injector(Protocol[T]):
    def __bevy_matches__(self, instance: T) -> bool:
        return False
