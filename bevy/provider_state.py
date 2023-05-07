from collections import UserDict
from typing import TypeVar

import bevy.repository

_K = TypeVar("_K")
_V = TypeVar("_V")


class ProviderState(UserDict[_K, _V]):
    """Each repository stores the state for each provider in a `ProviderState`. This allows the repository to share its
    providers with other repositories without needing to clone providers when branching. All dependencies that a
    provider handles is stored in that providers state on the repository."""

    def __init__(self, repository: "bevy.repository.Repository"):
        super().__init__()
        self.repository = repository
