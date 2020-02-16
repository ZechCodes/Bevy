from __future__ import annotations
from typing import Any, List, Dict, Optional, Tuple, Type, TypeVar, Union


GenericRepository = TypeVar("GenericRepository", bound="Repository")
GenericInstance = TypeVar("GenericInstance")
GenericType = Type[GenericInstance]
_NOVAL = object()


class Repository:
    def __init__(self, parent: Optional[GenericRepository] = None):
        self._parent = parent
        self._instance_repo: Dict[GenericType, GenericInstance] = {}

    def get(
        self, obj: GenericType, *, default: Any = _NOVAL, propagate: bool = True
    ) -> Optional[GenericInstance]:
        """ Get's an instance matching the requested type from the repository.
        If default is not set and an match is not found this will create an
        instance using the requested type. """
        if propagate and self._parent and not self.has(obj, propagate=False):
            return self._parent.get(obj, default=default)

        if not self.has(obj, propagate=False):
            if default is not _NOVAL:
                return default
            return self.set(obj, obj)
        return self._find(obj)

    def has(self, obj: GenericType, *, propagate: bool = True) -> bool:
        """ Checks if an instance matching the requested type exists in the
        repository. If a type is not provided this will raise an exception. """
        if not isinstance(obj, type):
            raise ExoRepositoryMustBeType(f"Repository expected a type received {obj}")

        return self._find(obj) is not _NOVAL or (
            propagate and self._parent and self._parent.has(obj)
        )

    def set(
        self, look_up_type: GenericType, instance: Union[GenericType, GenericInstance]
    ) -> GenericInstance:
        """ Sets the instance that should be returned when a given type is
        requested. This will raise exceptions if the look up type isn't a type
        and if the instance type is not an instance of the look up type. """
        if not isinstance(look_up_type, type):
            raise ExoRepositoryMustBeType(
                f"Repository expected a type received {look_up_type}"
            )

        value = instance() if isinstance(instance, type) else instance

        if not isinstance(value, look_up_type):
            raise ExoRepositoryMustBeMatchingTypes(
                f"Cannot set a value for mismatched types, received {look_up_type} and {instance}"
            )

        self._instance_repo[look_up_type] = value
        return value

    def _find(self, obj: GenericType) -> Union[GenericInstance, _NOVAL]:
        for obj_type in self._instance_repo:
            if issubclass(obj, obj_type):
                return self._instance_repo[obj_type]
        return _NOVAL

    @classmethod
    def create(
        cls,
        repo: Optional[Union[GenericRepository, Type[GenericRepository]]] = None,
        *args,
        **kwargs,
    ) -> GenericRepository:
        """ Return a repository object. If the repo provided is already
        instantiated it will be returned without change. If it is a subclass of
        Repository it will be instantiated with any args provided and returned.
        If neither of those is true Repository will be instantiated with the
        provided args and returned. The return is guaranteed to be an instance
        of Repository. """
        if isinstance(repo, Repository):
            return repo

        if repo and isinstance(repo, type) and issubclass(repo, Repository):
            return repo(*args, **kwargs)

        return cls(*args, **kwargs)


class ExoRepositoryMustBeType(Exception):
    ...


class ExoRepositoryMustBeMatchingTypes(Exception):
    ...
