from __future__ import annotations
from typing import Any, Protocol
import bevy


class Injector(Protocol):
    @classmethod
    def __bevy_inject__(
        cls,
        inject_into: Any,
        name: str,
        constructor: bevy.Constructor,
        *args,
        **kwargs,
    ):
        ...


def is_injector(cls) -> bool:
    return hasattr(cls, "__bevy_inject__")
