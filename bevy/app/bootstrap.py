from bevy import Context
from bevy.injectable import Injectable
from bevy.app.app import App
from bevy.app.settings import AppSettings
from bevy.config import Config, DirectoryResolver, JSONLoader
from bevy.config.loader import Loader
from bevy.config.resolver import Resolver
from pathlib import Path
from typing import Generic, Sequence, Type, TypeVar, Union


__all__ = ["Bootstrap"]


AppType = TypeVar("AppType", bound=App)


class Bootstrap(Generic[AppType]):
    def __init__(
        self,
        app_class: Injectable[Type[AppType]] = App,
        working_directory: Union[Path, str] = Path().resolve(),
        config_loaders: Sequence[Type[Loader]] = (JSONLoader,),
        config_resolvers: Sequence[Type[Resolver]] = (DirectoryResolver,),
    ):
        self._config_loaders = config_loaders
        self._config_resolvers = config_resolvers
        self._context = Context(app_class)
        self._working_directory = working_directory

    @property
    def context(self) -> Context[AppType]:
        return self._context

    def build(self) -> AppType:
        self.build_config()
        self.build_settings()
        return self.context.build()

    def build_config(self):
        self.context.add(
            Config(
                default_filename="app.settings",
                loaders=self._config_loaders,
                resolvers=tuple(
                    resolver(self._get_app_working_directory())
                    for resolver in self._config_resolvers
                ),
            )
        )

    def build_settings(self):
        settings = self.context.construct(
            AppSettings, self._get_app_working_directory()
        )
        self.context.add(settings)

    def create_app(self):
        app = self.context.build()
        self.context.add_as(app, App)
        return app

    def _get_app_working_directory(self) -> Path:
        path = Path(self._working_directory)
        # Handle if __file__ was passed
        if path.is_file():
            path = path.parent

        return path
