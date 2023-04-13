from bevy.providers import Provider
from bevy.results import Result, Success, Failure
from typing import Generic, TypeVar, Type
from bevy.contextvar import ContextVarDefaultFactory as _ContextVarDefaultFactory


_K = TypeVar("_K")
_V = TypeVar("_V")
_NOTSET = object()


class Repository(Generic[_K, _V]):
    """The Bevy repository manages instance providers and caching the results that the providers create."""
    _bevy_repository: "_ContextVarDefaultFactory[Repository[_K, _V]]" = _ContextVarDefaultFactory(
        "bevy_context",
        default=lambda: Repository()
    )

    def __init__(self):
        self._providers: list[Provider[_K, _V]] = []

    def add_providers(self, *providers: Type[Provider[_K, _V]]):
        """Creates providers and adds them to the repository. These providers will be used to lookup and create
        instances that will be stored and returned by the repository."""
        self._providers.extend(provider(self) for provider in providers)

    def create(self, key: _K) -> _V | None:
        """Attempts to create an instance of the type, returning None if no supporting provider was found."""
        for provider in self._providers:
            match provider.create(key):
                case Success(result):
                    return result

        return None

    def find(self, key: _K) -> Result[_V]:
        """Gets an instance from the repository, returning None if no match was found for the lookup type."""
        for provider in self._providers:
            match provider.find(key):
                case Success(_) as result:
                    return result

        return Failure(Exception(f"No match for {key!r} was found in the repository"))

    def get(self, key: _K) -> _V | None:
        """Gets an object from the repository, creating it if it doesn't exist and a provider is found that supports it,
        otherwise it will return None."""
        match self.find(key):
            case Success(result):
                return result
            case Failure(_):
                return self.create(key)

    @classmethod
    def get_repository(cls: "Type[Repository[_K, _V]]") -> "Repository[_K, _V]":
        return cls._bevy_repository.get()


get_repository = Repository.get_repository
