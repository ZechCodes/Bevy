from __future__ import annotations
from typing import Any, List, Dict, Optional, Tuple, Type, TypeVar, Union


GenericRepository = TypeVar("GenericRepository", bound="Repository")


class Repository:
    @classmethod
    def create(
        cls,
        repo: Optional[Union[GenericRepository, Type[GenericRepository]]] = None,
        *args,
        **kwargs
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
