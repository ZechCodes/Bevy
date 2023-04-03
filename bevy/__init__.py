from bevy.contextvar import ContextVarDefaultFactory as _ContextVarDefaultFactory
from bevy.context import Context


_bevy_context = _ContextVarDefaultFactory("bevy_context", default=Context)


def get_context() -> Context:
    return _bevy_context.get()