from bevy import Context, injectable
from bevy.events import EventDispatch
import pytest


NO_OP = type("NO_OP", (object,), {"__await__": lambda s: (None for _ in range(2))})()


@pytest.mark.asyncio
async def test_event_dispatch():
    @injectable
    class App:
        events: EventDispatch

    received = None

    async def watcher(payload):
        nonlocal received
        received = payload

    app = App()
    app.events.watch("test_event", watcher)
    await app.events.dispatch("test_event", "test payload")
    await NO_OP

    assert received == "test payload"
