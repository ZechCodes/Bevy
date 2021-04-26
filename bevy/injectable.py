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
from abc import ABCMeta
from bevy.context import Context
from bevy.injector import is_almost_injector
from typing import Any, Dict, Tuple, Type


class InjectableMeta(ABCMeta):
    """Metaclass for hooking into the object's call logic, allowing Bevy to insert itself just before dunder init is
    called and inject the required dependencies."""

    def __new__(mcs, name, bases, attrs):
        for a_name, a_type in attrs.get("__annotations__", {}).items():
            if is_almost_injector(a_type):
                raise TypeError(
                    f"{attrs['__module__']}.{name}.{a_name} was annotated as {a_type} which appears to be a Bevy "
                    f"injector but the __bevy_inject__ method is not a classmethod"
                )

        return super().__new__(mcs, name, bases, attrs)

    def __call__(cls: Type, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Injectable:
        """Creates a context object which is used to provide custom instantiation logic that injects the required
        dependencies before dunder init is called."""
        return Context().create(cls, *args, **kwargs)


class Injectable(metaclass=InjectableMeta):
    """ Base class that automates injection of required dependencies before dunder init is called. """

    pass
