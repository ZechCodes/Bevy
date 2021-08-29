from bevy.app.app import App
from bevy.app.bootstrap import Bootstrap
from bevy.app.settings import ExtensionLoadPolicy, ExtensionSettings
import asyncio
import pathlib
import pytest


async def clear_tasks():
    await asyncio.gather(
        *(
            task
            for task in asyncio.all_tasks()
            if not task.get_coro().__qualname__.startswith("test_")
        )
    )


@pytest.fixture()
def working_directory():
    return pathlib.Path(__file__).parent / "app"


def test_app_creation(working_directory):
    app = Bootstrap(working_directory=working_directory).build()
    assert isinstance(app, App)


def test_extension_load_policy_enabled_only():
    enabled = ExtensionSettings(
        "testing", {"enabled": True}, ExtensionLoadPolicy.ENABLED_ONLY
    )
    disabled = ExtensionSettings(
        "testing", {"enabled": False}, ExtensionLoadPolicy.ENABLED_ONLY
    )
    not_set = ExtensionSettings("testing", {}, ExtensionLoadPolicy.ENABLED_ONLY)
    assert enabled.enabled is True
    assert disabled.enabled is False
    assert not_set.enabled is False


def test_extension_load_policy_auto_load():
    enabled = ExtensionSettings(
        "testing", {"enabled": True}, ExtensionLoadPolicy.AUTO_ENABLE
    )
    disabled = ExtensionSettings(
        "testing", {"enabled": False}, ExtensionLoadPolicy.AUTO_ENABLE
    )
    not_set = ExtensionSettings("testing", {}, ExtensionLoadPolicy.AUTO_ENABLE)
    assert enabled.enabled is True
    assert disabled.enabled is False
    assert not_set.enabled is True


def test_extensions_found(working_directory):
    app = Bootstrap(working_directory=working_directory).build()
    extensions = {extension.name: extension.enabled for extension in app.all_extensions}
    assert {
        "ext_with_settings": True,
        "ext_disabled": False,
        "ext_no_settings": True,
    } == extensions


def test_extensions_loaded(working_directory):
    app = Bootstrap(working_directory=working_directory).build()
    extensions = {extension.name for extension in app.extensions}
    assert {"ext_with_settings", "ext_no_settings"} == extensions
