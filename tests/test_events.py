from bevy import Context, injectable
from bevy.events import EventDispatch
from collections import defaultdict
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


@pytest.mark.asyncio
async def test_event_dispatch_multiple_streams():
    @injectable
    class App:
        events_a: EventDispatch
        events_b: EventDispatch["B"]

    received = defaultdict(list)

    def create_watcher(key):
        async def watcher(payload):
            received[key].append(payload)

        return watcher

    app = App()
    app.events_a.watch("test_event", create_watcher("A"))
    app.events_b.watch("test_event", create_watcher("B"))

    await app.events_a.dispatch("test_event", "test payload a")
    await app.events_b.dispatch("test_event", "test payload b")
    await clear_tasks()

    assert received == {"A": ["test payload a"], "B": ["test payload b"]}


def test_invalid_stream_names():
    with pytest.raises(ValueError):
        EventDispatch[""]

    with pytest.raises(ValueError):
        EventDispatch[1337]
