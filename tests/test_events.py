from bevy import Context, injectable
from bevy.events import EventDispatch
import asyncio
import pytest


async def clear_tasks():
    await asyncio.gather(
        *(
            task
            for task in asyncio.all_tasks()
            if not task.get_coro().__qualname__.startswith("test_")
        )
    )


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
    await clear_tasks()

    assert received == "test payload"
