from collections import UserDict
from typing import TypeVar

import bevy.repository

_K = TypeVar("_K")
_V = TypeVar("_V")


class RepositoryCache(UserDict[_K, _V]):
    def __init__(self, repository: "bevy.repository.Repository"):
        super().__init__()
        self.repository = repository
