from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar, Union


ExoRepository = TypeVar("ExoRepository", bound="AbstractRepository")


class RepositoryNameExists(Exception):
    ...


class RepositoryNameDoesntExist(Exception):
    ...


class AbstractRepository(ABC):
    @property
    @abstractmethod
    def parent(self) -> ExoRepository:
        return NullRepository()

    @abstractmethod
    def create_child(self) -> ExoRepository:
        return NullRepository()

    @abstractmethod
    def get(self, cls: Type) -> Any:
        return

    @abstractmethod
    def has(self, cls: Type, *, propagate: bool = False) -> bool:
        return False

    def is_null(self) -> bool:
        return self is NullRepository()

    @abstractmethod
    def set(self, name: str, cls: Type) -> None:
        return


class NullRepository(AbstractRepository):
    """ Null singleton repository. """

    null_instance = None  # Holds the singleton instance

    def __new__(cls, *args, **kwargs):
        """ Caches a single instance that is always returned. """
        if not NullRepository.null_instance:
            NullRepository.null_instance = super().__new__(cls, *args, **kwargs)
        return NullRepository.null_instance

    def __init__(self, *args, **kwargs):
        pass

    @property
    def parent(self) -> ExoRepository:
        """ Returns a null repository. It is important that when traversing
        upwards through the parent hierarchy that there are checks for a null
        repository to prevent infinite loops/recursion. """
        return self

    def create_child(self) -> ExoRepository:
        return self

    def get(self, cls: Type) -> Any:
        """ Doesn't load anything and returns None instead. """
        return None

    def has(self, cls: Type, *, propagate: bool = False) -> bool:
        """ Doesn't have any instances. """
        return False

    def set(self, name: str, cls: Type) -> None:
        """ Doesn't set anything. """
        return


class Repository(AbstractRepository):
    """ Simple repository implementation for storing instances of classes for
    use by multiple objects. """

    def __init__(self, parent: ExoRepository = NullRepository()):
        self._parent = parent
        self._repository = {}

    @property
    def parent(self) -> ExoRepository:
        return self._parent

    def create_child(self) -> ExoRepository:
        return self.__class__(self)

    def get(self, cls: Union[str, Type]) -> Any:
        instance = self._get(cls)
        if not instance:
            if isinstance(cls, str):
                raise RepositoryNameDoesntExist(
                    f"The repository doesn't have the name {cls}"
                )
            instance = self._create_instance(cls)

        return instance

    def has(self, cls: Type, *, propagate: bool = True) -> bool:
        """ Checks if the repository or any of it's parents have an instance of
        the requested class. Propagation to parents can be disabled with the
        "propagate" boolean keyword argument. """
        if not propagate:
            return cls in self._repository

        return cls in self._repository or self.parent.has(cls)

    def set(self, name: str, cls: Type) -> None:
        """ Loads an instance into the repository as well as sets a name by
        which the instance can be retrieved. If the name already exists in the
        repository it will raise RepositoryNameExists. """
        if name in self._repository:
            raise RepositoryNameExists(
                f"The name {name} already exists in the repository."
            )
        self._repository[name] = self.get(cls)

    def _build_instance(self, cls: Type) -> Any:
        """ Builds an instance of a class. This will look for a
        __repository_build__ class method which it can call to get an instance
        built correctly for the repository. If that class method isn't found it
        will fallback to the standard Python constructor. """
        if hasattr(cls, "__repository_build__"):
            return cls.__repository_build__()

        return cls()

    def _create_instance(self, cls: Type) -> Any:
        """ Creates and stores an instance of a class placing it in the
        repository if appropriate. """
        instance = self._build_instance(cls)
        self._store_instance(instance, cls)
        return instance

    def _get(self, cls: Type) -> Any:
        """ Gets an instance of a class from the repository or it's parents if
        it has been created, returns None if it's not found. """
        if not self.has(cls):
            return None

        if cls in self._repository:
            return self._repository[cls]

        return self.parent.get(cls)

    def _store_instance(self, instance: Any, cls: Type):
        """ Stores an instance in the repository. It checks of an
        __repository_ignore__ class attribute that is set to True, if found it
        will ignore the instance and not store it. """
        if hasattr(cls, "__repository_ignore__") and cls.__repository_ignore__:
            return

        self._repository[cls] = instance
