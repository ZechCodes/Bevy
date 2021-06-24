from functools import partial
from typing import Any
import bevy


class Factory:
    """Simple factory implementation that creates a callable bound to the constructor context and that will return the
    annotated type when called.

    Example:

    class Example(Injectable):
        factory: Factory[Thing]
        ...
        self.factory(args...)
    """

    def __init__(self, item: Any):
        self._item = item

    def __bevy_inject__(
        self,
        inject_into: Any,
        name: str,
        constructor: bevy.Constructor,
        *args,
        **kwargs
    ):
        setattr(inject_into, name, partial(constructor.construct, self._item))

    def __class_getitem__(cls, item):
        return Factory(item)
