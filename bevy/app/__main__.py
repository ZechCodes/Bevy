from bevy.app.bootstrap import Bootstrap
from bevy.app.app import App
from pathlib import Path


Bootstrap(App, Path().resolve()).build().run()
