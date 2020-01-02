from __future__ import annotations
from functools import cached_property
from typing import Any, Dict, Generic, TypeVar


GenericBase = TypeVar("GenericBase")


class Repository(Generic[GenericBase]):
    """\
    Simple registry implementation that provides a helper class that can be
    subclassed
    """
    def __init__(self, base: GenericBase):
        self._base = base
        self._registry: Dict[str, GenericBase] = {}

    @property
    def registry(self) -> Dict[str, GenericBase]:
        """ Provides a copy of the internal registry. """
        return self._registry.copy()

    def register(self, cls: GenericBase) -> Repository:
        """ Adds a class to the registry. """
        self._registry[cls.__name__] = cls
        return self

    def unregister(self, cls: GenericBase) -> Repository:
        """ Removes a class from the registry. """
        if cls.__name__ in self._registry:
            del self._registry[cls.__name__]
        return self

    @cached_property
    def registration_subclass(self):
        """\
        Generates a subclass of base that supplies an implementation of
        __init_subclass__ that will register the class with the repository.
        """

        repository = self  # For clarity

        class Intermediary(self._base):
            def __init_subclass__(cls, **kwargs):
                super().__init_subclass__(**kwargs)
                repository.register(cls)

        return Intermediary
