from bevy.extensions.config.resolver import Reader
from json import loads, dumps
from typing import Any, Protocol, runtime_checkable


class JSONLoader:
    file_types = ("json",)

    def __init__(self, reader: Reader):
        self.reader = reader

    def load(self) -> dict[str, Any]:
        return loads(self.reader.read())

    def save(self, data: dict[str, Any]):
        self.reader.save(dumps(data))


def is_loader(obj):
    return isinstance(obj, Loader)
