from bevy.providers import Provider
from bevy.results import Result, Success, Failure
from typing import Generic, TypeVar, Type
from bevy.contextvar import ContextVarDefaultFactory as _ContextVarDefaultFactory


_T = TypeVar("_T")
_V = TypeVar("_V")
_NOTSET = object()


class Repository(Generic[_T, _V]):
    """The Bevy repository manages instance providers and caching the results that the providers create."""
    _bevy_repository: "_ContextVarDefaultFactory[Repository[_T, _V]]" = _ContextVarDefaultFactory(
        "bevy_context",
        default=lambda: Repository()
    )

    def __init__(self):
        self._providers: list[Provider[_T, _V]] = []

    def add_providers(self, *providers: Type[Provider[_T, _V]]):
        """Creates providers and adds them to the repository. These providers will be used to lookup and create
        instances that will be stored and returned by the repository."""
        self._providers.extend(provider(self) for provider in providers)

    def create(self, new_type: _T) -> _V | None:
        """Attempts to create an instance of the type, returning None if no supporting provider was found."""
        for provider in self._providers:
            match provider.create(new_type):
                case Success(result):
                    return result

        return None

    def find(self, lookup: _T) -> Result[_V]:
        """Gets an instance from the repository, returning None if no match was found for the lookup type."""
        for provider in self._providers:
            match provider.find(lookup):
                case Success(_) as result:
                    return result

        return Failure(Exception(f"No match for {lookup!r} was found in the repository"))

    def get(self, lookup: _T) -> _V | None:
        """Gets an object from the repository, creating it if it doesn't exist and a provider is found that supports it,
        otherwise it will return None."""
        match self.find(lookup):
            case Success(result):
                return result
            case Failure(_):
                return self.create(lookup)

    @classmethod
    def get_repository(cls: "Type[Repository[_T, _V]]") -> "Repository[_T, _V]":
        return cls._bevy_repository.get()


get_repository = Repository.get_repository
