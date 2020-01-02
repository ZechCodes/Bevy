from __future__ import annotations
from abc import ABCMeta, abstractmethod
from exo.exceptions import AppMustUseExoSubclass
from exo.extension import Extension, get_extensions
from exo.repository import Repository
from typing import Any, Dict, Tuple, Type


class ExoMeta(ABCMeta):
    def __new__(
        mcs, name: str, bases: Tuple[Type[Exo]], attrs: Dict[str, Any]
    ) -> Type[Exo]:
        """ Create an Exo app class that is preloaded with all known extensions. """
        if bases:
            attrs.update(mcs.create_extension_repositories())
        return super().__new__(mcs, name, bases, attrs)

    def __call__(cls, *args, **kwargs) -> Type[Exo]:
        """ Prevent the instantiation of the base Exo class. """
        if cls == Exo:
            raise AppMustUseExoSubclass(
                "You must create a custom App class that is a subclass of the Exo base class."
            )
        return super().__call__(*args, **kwargs)

    @staticmethod
    def create_extension_repositories() -> Dict[str, Type[Extension]]:
        """\
        Gets all extensions that have been registered and then creates a
        repository and exposes the auto registration subclass for each one.
        """

        attrs = {}
        repositories = attrs["__repositories__"] = {}
        for name, extension in get_extensions().items():
            repo = repositories[name] = Repository(extension)
            attrs[name] = repo.registration_subclass
        return attrs


class Exo(metaclass=ExoMeta):
    ...
