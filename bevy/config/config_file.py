from bevy.config.loader import Loader
from typing import Any


class ConfigFile:
    def __init__(self, loader: Loader):
        self._loader = loader
        self._data = None

    @property
    def config_data(self) -> dict[str, Any]:
        if not self._data:
            self._data = self._loader.load()

        return self._data

    def get_section(self, name: str) -> Any:
        return self.config_data.get(name)
