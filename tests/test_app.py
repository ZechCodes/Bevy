from bevy.app.app import App
from bevy.app.bootstrap import Bootstrap
import asyncio
import pathlib
import pytest


@pytest.fixture()
def working_directory():
    return pathlib.Path(__file__).parent / "app" / "extensions"


def test_app_creation(working_directory):
    app = Bootstrap(working_directory).build()
    assert isinstance(app, App)
