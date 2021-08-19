from __future__ import annotations
from bevy.events.event import Event
from gully import Gully, Callback, Observer
from typing import Generic, Type, TypeVar


T = TypeVar("T")


class EventDispatch:
    def __init__(self, name: str = ""):
        self._gully = Gully()
        self._event_streams = {}
        self._name = name

    @property
    def name(self) -> str:
        return self._name

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

    def __class_getitem__(cls, item: str) -> EventDispatchBuilder[EventDispatch]:
        if not item or not isinstance(item, str):
            raise ValueError(
                f"{cls.__name__} only accepts stream names that are non-empty strings"
            )
        return EventDispatchBuilder(item, cls)

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"


class EventDispatchBuilder(Generic[T]):
    def __init__(self, name: str, dispatch_type: Type[T]):
        self.name = name
        self.dispatch_type = dispatch_type

    def __call__(self, *args, **kwargs) -> T:
        return self.dispatch_type(self.name)

    def __bevy_is_match__(self, obj):
        if not isinstance(obj, EventDispatchBuilder):
            return False

        return obj.name == self.name

    def __repr__(self):
        return f"{self.dispatch_type.__name__}({self.name!r})"
