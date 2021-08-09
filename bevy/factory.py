from functools import partial
from typing import Any
from bevy import Context


class Factory:
    """Simple factory implementation that creates a callable bound to the context context and that will return the
    annotated type when called.

    **Example**
    ```python
    class Thing:
        def __init__(self, name):
            self.name = name

    class Example(Injectable):
        factory: Factory[Thing]
        ...
        def create_thing(self, name: str):
            self.factory(name)
    ```
    """

    def __init__(self, item: Any):
        self._item = item

    def __bevy_inject__(self, inject_into: Any, name: str, context: Context):
        setattr(inject_into, name, partial(context.construct, self._item))

    def __class_getitem__(cls, item):
        return Factory(item)
