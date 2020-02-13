from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Iterable, Type, TypeVar, Union


ExoRepository = TypeVar("ExoRepository", bound="AbstractRepository")
NULL_VALUE = object()


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
    def get(self, name: str, *, default: Any = None, instantiate: bool = True) -> Any:
        return

    @abstractmethod
    def has(self, name: str, *, propagate: bool = False) -> bool:
        return False

    def is_null(self) -> bool:
        return self is NullRepository()

    @abstractmethod
    def set(self, name: str, obj: Any, *, instantiate: bool = True) -> None:
        return

    @abstractmethod
    def __iter__(self) -> Iterable:
        return tuple()


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

    def __iter__(self) -> Iterable:
        return tuple()

    @property
    def parent(self) -> ExoRepository:
        """ Returns a null repository. It is important that when traversing
        upwards through the parent hierarchy that there are checks for a null
        repository to prevent infinite loops/recursion. """
        return self

    def create_child(self) -> ExoRepository:
        return self

    def get(self, name: str, *, default: Any = None, instantiate: bool = True) -> Any:
        """ Doesn't load anything and returns None instead. """
        return None

    def has(self, name: str, *, propagate: bool = False) -> bool:
        """ Doesn't have any instances. """
        return False

    def set(self, name: str, obj: Any, *, instantiate: bool = True) -> None:
        """ Doesn't set anything. """
        return


class Repository(AbstractRepository):
    """ Simple repository implementation for storing instances of classes for
    use by multiple objects. """

    def __init__(self, parent: ExoRepository = NullRepository()):
        self._parent = parent
        self._repository = {}

    def __iter__(self) -> Iterable:
        yield from self._repository.items()

    @property
    def parent(self) -> ExoRepository:
        return self._parent

    def create_child(self) -> ExoRepository:
        return self.__class__(self)

    def get(
        self, name: str, *, default: Any = NULL_VALUE, instantiate: bool = True
    ) -> Any:
        if not self.has(name):
            if default is NULL_VALUE:
                raise RepositoryNameDoesntExist(
                    f"The repository doesn't have anything registered with the name '{name}'"
                )
            self.set(name, default, instantiate=instantiate)

        return self._get(name)

    def has(self, name: str, *, propagate: bool = True) -> bool:
        """ Checks if the repository or any of it's parents have an instance of
        the requested class. Propagation to parents can be disabled with the
        "propagate" boolean keyword argument. """
        if not propagate:
            return name in self._repository

        return name in self._repository or self.parent.has(name)

    def set(
        self,
        name: str,
        obj: Any,
        *,
        instantiate: bool = True,
        repository: ExoRepository = None,
    ) -> None:
        """ Loads an object into the repository. If the object should be not be
        instantiated the instantiate keyword should be set to False. If the
        name already exists in the repository it will raise
        RepositoryNameExists. name must be hashable. """
        if self.has(name, propagate=False):
            raise RepositoryNameExists(
                f"The name {name} already exists in the repository."
            )
        self._repository[name] = RepositoryElement(
            obj, repository if repository else self, instantiate
        )

    def _get(self, name: str) -> Union[Any, NULL_VALUE]:
        """ Gets a value from the repository or it's parents if it has been
        registered, returns None if it's not found. """
        if not self.has(name):
            return NULL_VALUE

        if name in self._repository:
            return self._repository[name].instance

        return self.parent.get(name)


class RepositoryElement:
    def __init__(self, obj: Any, repository: ExoRepository, instantiate: bool = True):
        self.instance = NULL_VALUE if instantiate else obj
        self.instantiate = instantiate
        self.obj = obj
        self._repository = repository

    @property
    def cacheable(self) -> bool:
        return not (
            hasattr(self.obj, "__repository_ignore__")
            and self.obj.__repository_ignore__
        )

    @property
    def instance(self) -> Any:
        instance = self._instance
        if self._instance is NULL_VALUE:
            instance = self._create_instance()
        if self.cacheable:
            self._instance = instance
        return instance

    @instance.setter
    def instance(self, value: Any):
        self._instance = value

    @property
    def instantiate(self) -> bool:
        return self._instantiate

    @instantiate.setter
    def instantiate(self, value: bool):
        self._instantiate = value

    @property
    def obj(self) -> Any:
        return self._obj

    @obj.setter
    def obj(self, value: Any):
        self._obj = value

    def _create_instance(self):
        """ Builds an instance of a class. This will look for a
        __repository_build__ class method which it can call to get an instance
        built correctly for the repository. If that class method isn't found it
        will fallback to the standard Python constructor. """
        if hasattr(self.obj, "__repository_build__"):
            return self.obj.__repository_build__(self._repository)

        return self.obj(__repository__=self._repository)
