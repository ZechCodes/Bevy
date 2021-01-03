""" Bevy Factory adds a generic factory mechanism that can be used to create instances of any class with all required
dependencies pulled from the a shared Context repository.

Here's an example of how to use a Bevy Factory.

>>> class Dependency:
...     def __init__(self, word: str):
...         self.word = word
...     def print_word(self):
...         print(self.word)
>>> class Example(Injectable):
...     dep_factory: Factory[Dependency]
...     def create_printer(self, word: str) -> Dependency:
...         return self.dep_factory()
>>> foo_printer = Example().create_printer("foo")
>>> foo_printer.print_word()
"""


from __future__ import annotations
from typing import Generic, Type, TypeVar
import bevy.context


T = TypeVar("T")


class Factory(Generic[T]):
    """Generic factory that creates instances of a class using a given Bevy Context. This object can be used as an
    annotation using the class get item syntaxt:

    >>> class Example(Injectable):
    ...     example_factory: Factory[Dependency]
    """

    def __init__(self, build_type: Type[T], context: bevy.context.BaseContext):
        self.build_type = build_type
        self.context = context

    def __call__(self, *args, **kwargs) -> T:
        """ Create an instance of the class using the context to inject the required dependencies. """
        return self.context.create(self.build_type, *args, **kwargs)

    def __class_getitem__(cls, build_type: Type[T]) -> FactoryAnnotation[T]:
        """ Make the factory object function as an annotation. """
        return FactoryAnnotation(build_type, cls)


class FactoryAnnotation(Generic[T]):
    """ The factory annotation acts as a factory of factories, creating factories that are bound to a context. """

    def __init__(self, build_type: Type[T], factory: Type[Factory]):
        self.build_type = build_type
        self.factory = factory

    def create_factory(self, context: bevy.context.BaseContext) -> Factory[Type[T]]:
        """ Creates a new factory that is bound to the given context. """
        return self.factory(self.build_type, context)
