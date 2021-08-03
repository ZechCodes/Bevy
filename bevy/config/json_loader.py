from bevy.config.resolver import Reader
from json import loads, dumps
from typing import Any


class JSONLoader:
    file_types = ("json",)

    def __init__(self, reader: Reader):
        self.reader = reader

    def load(self) -> dict[str, Any]:
        return loads(self.reader.read())

    def save(self, data: dict[str, Any]):
        self.reader.save(dumps(data))
