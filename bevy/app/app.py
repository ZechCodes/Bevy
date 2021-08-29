from bevy import injectable
from bevy.app.importing import import_module_from_path
from bevy.app.settings import AppSettings, ExtensionSettings
from typing import Generator, Optional
from types import ModuleType
from site import addsitedir


@injectable
class App:
    settings: AppSettings

    def __init__(self):
        self._extensions = tuple(self._get_extensions())
        self._load_extensions()

    @property
    def extensions(self) -> tuple[ExtensionSettings]:
        return tuple(
            extension for extension in self.all_extensions if extension.enabled
        )

    @property
    def all_extensions(self) -> tuple[ExtensionSettings]:
        return self._extensions

    def _load_extensions(self):
        addsitedir(self.settings.extensions_path)
        modules = (
            self._load_extension(extension)
            for extension in self._extensions
            if extension.enabled
        )

    def _load_extension(self, extension: ExtensionSettings) -> ModuleType:
        return import_module_from_path(self.settings.extensions_path, extension.name)

    def _get_extensions(self) -> Generator[ExtensionSettings, None, None]:
        for name in self.settings.extensions_path.iterdir():
            if name.is_file() and name.suffix.casefold() != ".py":
                continue

            if name.stem[0] in {".", "_"}:
                continue

            extension = self.settings.extensions.get(name.stem)
            if not extension:
                extension = self.settings.create_extension_settings(name.stem, {})

            yield extension
