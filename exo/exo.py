from __future__ import annotations
from typing import Any, List, Dict, Optional, Tuple, Type, TypeVar, Union


GenericExo = TypeVar("GenericExo", bound="Exo")


class ExoMeta(type):
    def __new__(mcs, name: str, bases: Tuple[Type], attrs: Dict[str, Any]):
        """ Find and inherit all dependencies. """
        mcs._build_dependencies(attrs, bases)
        return super().__new__(mcs, name, bases, attrs)

    @staticmethod
    def _build_dependencies(attrs: Dict[str, Any], bases: Tuple[Type]):
        """ Builds a dictionary of dependencies from the annotated properties
        that are found on the bases and in the class definition. These
        dependencies are stored in the __dependencies__ attribute of the class.
        """
        dependencies = {}
        for base in bases:
            if hasattr(base, "__dependencies__"):
                dependencies.update(base.__dependencies__)

        dependencies.update(
            {
                name: dependency
                for name, dependency in attrs.get("__annotations__", {}).items()
                if issubclass(dependency, Exo)
            }
        )

        attrs["__dependencies__"] = dependencies


class Exo(metaclass=ExoMeta):
    __dependencies__ = {}  # This is so IDEs don't complain, overridden in the metaclass
