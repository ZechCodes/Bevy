from __future__ import annotations
from bevy import injectable
from bevy.config import Config
from collections import UserDict
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ExtensionLoadPolicy(str, Enum):
    # The extension will not be loaded unless enabled is set to true in the app.settings file
    ENABLED_ONLY = "ENABLED_ONLY"
    # The extension will be loaded unless enabled is set to false in the app.settings file
    AUTO_ENABLE = "AUTO_ENABLE"


@injectable
class AppSettings:
    loader: Config

    def __init__(self, working_directory: Path):
        self._config = self.loader.get_config_file()
        self._extensions: Optional[dict[str, ExtensionSettings]] = None
        self._options: Optional[dict[str, Any]] = None
        self._path = working_directory

    @property
    def extensions(self) -> dict[str, ExtensionSettings]:
        if self._extensions is None:
            self._create_extension_settings()

        return self._extensions

    @property
    def extensions_path(self) -> Path:
        return self.options["extension_directory"]

    @property
    def options(self) -> dict[str, Any]:
        if self._options is None:
            self._create_options()

        return self._options

    @property
    def path(self) -> Path:
        return self._path

    def _create_extension_settings(self):
        self._extensions = {
            name: self.create_extension_settings(name, value)
            for name, value in self._config.get_section("extensions").items()
        }

    def create_extension_settings(self, name: str, value: Any) -> ExtensionSettings:
        return ExtensionSettings(name, value, self.options["extension_load_policy"])

    def _create_options(self):
        options = self._config.get_section("options") or {}
        if "extension_load_policy" in options:
            options["extension_load_policy"] = ExtensionLoadPolicy(
                options["extension_load_policy"].upper()
            )

        if "extension_directory" in options:
            options["extension_directory"] = self._resolve_extension_directory(
                options["extension_directory"]
            )

        self._options = {
            "extension_directory": self.path,
            "extension_load_policy": ExtensionLoadPolicy.AUTO_ENABLE,
        }
        self.options.update(options)

    def _resolve_extension_directory(self, directory: str) -> Path:
        path = Path(directory)
        if not path.is_absolute():
            path = self.path / path
        return path.resolve()


class ExtensionSettings(UserDict):
    def __init__(self, name: str, settings: Any, load_policy: ExtensionLoadPolicy):
        self._name = name
        self._load_policy = load_policy
        self._locked = False
        super().__init__(self._process_settings(settings))
        self._locked = True

    @property
    def enabled(self) -> Optional[bool]:
        return self._is_enabled()

    @property
    def name(self) -> str:
        return self._name

    def _is_enabled(self) -> bool:
        return bool(
            self.get("enabled", self._load_policy == ExtensionLoadPolicy.AUTO_ENABLE)
        )

    def _process_settings(self, settings: Any) -> dict[str, Any]:
        if isinstance(settings, bool):
            return {"enabled": settings}

        if isinstance(settings, dict):
            return settings

        return {}

    def __setitem__(self, key, value):
        if self._locked:
            raise TypeError("You cannot change an extension setting")
        super().__setitem__(key, value)

    def __repr__(self):
        settings = dict(self)
        settings.setdefault("enabled", self.enabled)
        return f"{type(self).__name__}({self.name!r}, {settings})"
