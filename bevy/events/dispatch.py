from bevy.events.event import Event
from gully import Gully, Callback, Observer


class EventDispatch:
    def __init__(self):
        self._gully = Gully()
        self._event_streams = {}

    async def dispatch(self, event_name: str, *args, **kwargs):
        """Creates an event with the args payload and pushes it into the gully event stream."""
        await self._gully.push(Event(event_name, *args, **kwargs))

    def watch(self, event_name: str, callback: Callback) -> Observer:
        """Watch an event. Returns a gully.Observer that allows enabling and disabling the watcher."""

        async def watcher(event: Event):
            await callback(*event.payload_args, **event.payload_kwargs)

        stream = self._get_event_stream(event_name)
        return stream.watch(watcher)

    def _get_event_stream(self, event_name: str) -> Gully:
        try:
            return self._event_streams[event_name]
        except KeyError:
            return self._create_event_stream(event_name)

    def _create_event_stream(self, event_name: str) -> Gully:
        async def event_filter(event: Event) -> bool:
            return event.name == event_name

        self._event_streams[event_name] = self._gully.filter(event_filter)
        return self._event_streams[event_name]
