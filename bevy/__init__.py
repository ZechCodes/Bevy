from bevy.contextvar import ContextVarDefaultFactory as _ContextVarDefaultFactory
from bevy.repository import Repository


_bevy_repository = _ContextVarDefaultFactory("bevy_context", default=Repository)


def get_repository() -> Repository:
    return _bevy_repository.get()
