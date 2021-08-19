# Bevy.Events
Bevy.Events is an events system designed to be used with the [Bevy](https://github.com/ZechCodes/Bevy) dependency injection framework. It uses [Gully](https://github.com/ZechCodes/Gully) for creating observable streams of event objects.

## Installation
```shell script
pip install bevy.events
```

**Documentation**

Bevy.Events is incredibly straightforward. You can use it as an annotation type on any injectable class.
```python
@bevy.injectable
class Example:
    events: bevy.events.EventDispatch
    ...
```
It is also possible to have multiple event dispatchers in the same Bevy context by giving them names. 
```python
@bevy.injectable
class Example:
    events: bevy.events.EventDispatch["my-event-dispatch"]
    ...
```
To send an event use the `dispatch` on the event dispatch and pass it the event name to dispatch and all the args to pass to the watchers.
```python
@bevy.injectable
class Example:
    events: bevy.events.EventDispatch
    ...

    async def recieved_message(self, message):
        await self.dispatch("message-received", message)
```
To register a watcher just call `watch` on the event dispatch and pass it an event name to `watch` for and a coroutine callback. The callback will be passed all args that were given to the `dispatch` method.
```python
@bevy.injectable
class Example:
    events: bevy.events.EventDispatch
    def __init__(self):
        self.events.watch("message-received", self.on_message_received)
    async def on_message_received(self, message):
        ...
```
`watch` returns a [Gully observer](https://github.com/ZechCodes/Gully#gullyobservablegullygully) so that the event watcher can be enabled or disabled as needed.

The event dispatchers will be shared by all class instances in the Bevy context. Events dispatched on a named dispatcher will only be sent to watchers of that event dispatcher. Any class in the context can access the same same event dispatcher just by giving the annotation the same name.
