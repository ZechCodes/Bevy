from bevy import injectable
from bevy.app.settings import AppSettings


@injectable
class TestApp:
    settings: AppSettings
