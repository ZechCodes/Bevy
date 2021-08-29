from bevy import injectable
from bevy.app.settings import AppSettings
from ext_disabled import TestApp


@injectable
class TestApp:
    settings: AppSettings
