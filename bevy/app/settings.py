from __future__ import annotations
from bevy import injectable
from bevy.config import Config
from collections import UserDict
from enum import Enum
from importlib import import_module, machinery, util
from pathlib import Path
from typing import Any, Optional
import sys


class ExtensionLoadPolicy(str, Enum):
    # The extension will not be loaded unless enabled is set to true in the app.settings file
    EXPLICIT_ENABLE = "EXPLICIT_ENABLE"
    # The extension will be loaded unless enabled is set to false in the app.settings file
    EXPLICIT_DISABLE = "EXPLICIT_DISABLE"
    # The extension will be loaded only if it is in the app.settings file and enabled isn't set to false
    AUTO_ENABLE = "AUTO_ENABLE"


@injectable
class AppSettings:
    loader: Config

    def __init__(self, working_directory: Path):
        self._config = self.loader.get_config_file()
        self._extensions: Optional[list[ExtensionSettings]] = None
        self._options: Optional[dict[str, Any]] = None

    @property
    def extensions(self) -> list[ExtensionSettings]:
        if self._extensions is None:
            self._create_extension_settings()

        return self._extensions

    @property
    def options(self) -> dict[str, Any]:
        if self._options is None:
            self._create_options()

        return self._options

    def _create_extension_settings(self):
        self._extensions = [
            ExtensionSettings(
                name, value if isinstance(value, dict) else {"enabled": bool(value)}
            )
            for name, value in self._config.get_section("extensions").items()
        ]

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

        if "extension_loader" in options:
            options["extension_loader"] = self._get_module_attr_from_string(
                options["extension_loader"]
            )

        self._options = {
            "extension_directory": self.path,
            "extension_load_policy": ExtensionLoadPolicy.AUTO_ENABLE,
            "extension_loader": self._extension_loader,
        }
        self.options.update(options)

    def _extension_loader(self):
        ...

    def _resolve_extension_directory(self, directory: str) -> Path:
        path = Path(directory)
        if not path.is_absolute():
            path = self.path / path
        return path.resolve()

    def _get_module_attr_from_string(self, lookup: str) -> Any:
        module_name, attr_name = map(str.strip, lookup.split(":"))
        module = self._import_module(module_name)
        return getattr(module, attr_name)

    def _get_module_attr_from_path(self, module_name: str, attr_name: str) -> Any:
        path = self._get_module_path(module_name)
        module = self._import_module_from_path(module_name)
        return getattr(module, attr_name)

    def _get_module_path(self, module_name: str) -> Path:
        path = self.path / f"{module_name}.py"
        if not path.exists():
            path = path / module_name / "__init__.py"
        return path.resolve()

    def _import_module(self, module_name: str):
        return import_module(module_name)

    def _import_module_from_path(self, module: str):
        finder = machinery.FileFinder(
            str(self.path),
            (
                machinery.SourceFileLoader,
                [".py"],
            ),
        )
        spec = finder.find_spec(module)
        if spec.name in sys.modules:
            return sys.modules[spec.name]

        module = util.module_from_spec(spec)
        sys.modules[spec.name] = module

        spec.loader.exec_module(module)
        return module


class ExtensionSettings(UserDict):
    def __init__(self, name: str, settings: dict[str, Any]):
        self._name = name
        self._locked = False
        super().__init__(settings)
        self._locked = True

    @property
    def enabled(self) -> Optional[bool]:
        return self.get("enabled")

    @property
    def name(self) -> str:
        return self._name

    def __setitem__(self, key, value):
        if self._locked:
            raise TypeError("You cannot change an extension setting")
        super().__setitem__(key, value)

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r}, {super().__repr__()})"