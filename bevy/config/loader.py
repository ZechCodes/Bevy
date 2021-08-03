from bevy.config.resolver import Reader
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Loader(Protocol):
    file_types: tuple[str]

    def __init__(self, reader: Reader):
        ...

    def load(self) -> dict[str, Any]:
        ...

    def save(self, data: dict[str, Any]):
        ...


def is_loader(obj):
    return isinstance(obj, Loader)
