from __future__ import annotations
from typing import Any, Protocol
import bevy


class Injector(Protocol):
    """Protocol that allows a class to modify how and what it injects into another class.

    When a class is being instantiated and having it's dependencies injected, Bevy will check if the dependency
    implements the injector protocol. If it does the __bevy_inject__ method will be called and should handle injecting
    into the class. This should include constructing whatever dependency is being injected."""

    @classmethod
    def __bevy_inject__(
        cls,
        inject_into: Any,
        name: str,
        context: bevy.Context,
        *args,
        **kwargs,
    ):
        ...


def is_injector(cls) -> bool:
    return hasattr(cls, "__bevy_inject__")
