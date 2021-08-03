from bevy import Constructor, injectable
from bevy.config import Config, DirectoryResolver, JSONLoader
from pathlib import Path


def test_config():
    @injectable
    class App:
        config: Config["app"]

    builder = Constructor(App)
    builder.add(
        Config(
            loaders=[JSONLoader],
            resolvers=[DirectoryResolver(Path(__file__).parent / "config_files")],
        )
    )
    app = builder.build()
    assert app.config["name"] == "test_app"
