from bevy.app.app import App
from bevy.app.bootstrap import Bootstrap
from bevy.app.settings import ExtensionLoadPolicy, ExtensionSettings
import asyncio
import pathlib
import pytest


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


def test_extensions_loaded(working_directory):
    app = Bootstrap(working_directory=working_directory).build()
    extensions = {extension.name: extension.enabled for extension in app.extensions}
    assert {
        "ext_with_settings": True,
        "ext_disabled": False,
        "ext_no_settings": True,
    } == extensions
