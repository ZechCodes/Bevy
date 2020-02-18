from __future__ import annotations
from exo.repository import GenericRepository, Repository
from typing import Any, Dict, Optional, Tuple, Type, TypeVar


GenericExo = TypeVar("GenericExo", bound="Exo")


class ExoMeta(type):
    def __new__(mcs, name: str, bases: Tuple[Type], attrs: Dict[str, Any]):
        """ Find and inherit all dependencies. """
        mcs._build_dependencies(attrs, bases)
        return super().__new__(mcs, name, bases, attrs)

    def __call__(
        cls: GenericExo,
        *args,
        __repository__: Optional[GenericRepository] = None,
        **kwargs
    ):
        repo = Repository.create(__repository__)
        instance = cls.__new__(cls, *args, **kwargs)
        if instance.__class__ is cls:
            instance.__repository__ = repo
            instance.__inject_dependencies__()
            instance.__init__(*args, **kwargs)
        return instance

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
                if name not in attrs
            }
        )

        attrs["__dependencies__"] = dependencies


class Exo(metaclass=ExoMeta):
    __dependencies__ = {}  # This is so IDEs don't complain, overridden in the metaclass
    __repository__: GenericRepository = None  # This is so IDEs don't complain, overridden in the metaclass

    def __inject_dependencies__(self):
        for name, dependency in self.__dependencies__.items():
            setattr(self, name, self.__repository__.get(dependency))
