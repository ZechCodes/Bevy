from bevy import Context, injectable
from bevy.app.app import App
from bevy.app.settings import AppSettings
from bevy.config import Config, DirectoryResolver, JSONLoader
from bevy.label import Label
from pathlib import Path
from typing import Union


__all__ = ["main"]


@injectable
class Bootstrap:
    context: Context
    path: Label[Path:"app"]
    settings: AppSettings

    def run(self):
        app = self.create_app()
        self.load_extensions()

    def create_app(self):
        app = self.context.construct(self.settings.options["app_class"])
        self.context.add_as(app, App)
        return app


def main(app_path: Union[str, Path]):
    app_directory = get_app_path(app_path)
    config_loader = get_config_loader(app_directory)
    bootstrap = create_bootstrap(app_directory, config_loader)
    bootstrap.run()


def create_bootstrap(path: Path, loader: Config) -> Bootstrap:
    context = Context(Bootstrap)
    context.add(Label(path, "app_path"))
    context.add(loader)
    return context.build()


def get_app_path(app_path: Union[str, Path]) -> Path:
    path = Path(app_path)
    # Handle if __file__ was passed
    if path.is_file():
        path = path.parent
    return path.resolve()


def get_config_loader(app_directory: Path) -> Config:
    return Config(
        default_filename="app.settings",
        loaders=(JSONLoader,),
        resolvers=(DirectoryResolver(app_directory),),
    )
