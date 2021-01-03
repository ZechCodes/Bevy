""" Base classes for any Bevy injectable classes.

The Injectable base class allows a class to have its dependencies created and injected at instantiation (when the class
object is called). This is accomplished by using a metaclass to hook into the class object's dunder call method, it then
creates a Context which is used to create an instance of the class. A metaclass is used so that subclasses of Injectable
can provide their own custom dunder new logic without needing to worry about the internal logic of Context. Using a
metaclass has the added benfit of allowing Bevy to inject the requested dependencies without needing to inject any of
Bevy's own state into the object.

Here is an example of how to use Injectable.

>>> class Dependency:
...     def print_something(self):
...          print("Something")
>>> class Example(Injectable):
...     dep: Dependency
...     def print_something(self):
...         self.dep.print_something()
>>> example = Example()
>>> example.print_something()
"""

from __future__ import annotations
from bevy.context import Context
from typing import Any, Dict, Tuple, Type


class InjectableMeta(type):
    """Metaclass for hooking into the object's call logic, allowing Bevy to insert itself just before dunder init is
    called and inject the required dependencies."""

    def __call__(
        cls: Type[Injectable], *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> Injectable:
        """Creates a context object which is used to provide custom instantiation logic that injects the required
        dependencies before dunder init is called."""
        return Context().create(cls, *args, **kwargs)


class Injectable(metaclass=InjectableMeta):
    """ Base class that automates injection of required dependencies before dunder init is called. """

    pass
