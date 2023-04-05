from bevy.providers import Provider
from bevy.results import Result, Success, Failure
from typing import Any, TypeVar, Type


T = TypeVar("T")
_NOTSET = object()


class Repository:
    """The Bevy repository manages instance providers and caching the results that the providers create."""
    def __init__(self):
        self._providers: list[Provider] = []

    def add_providers(self, *providers: Type[Provider]):
        """Creates providers and adds them to the repository. These providers will be used to lookup and create
        instances that will be stored and returned by the repository."""
        self._providers.extend(provider(self) for provider in providers)

    def create(self, new_type: Type[T]) -> T | None:
        """Attempts to create an instance of the type, returning None if no supporting provider was found."""
        for provider in self._providers:
            match provider.create(new_type):
                case Success(result):
                    return result

        return None

    def find(self, lookup_type: Type[T]) -> Result[T]:
        """Gets an instance from the repository, returning None if no match was found for the lookup type."""
        for provider in self._providers:
            match provider.find(lookup_type):
                case Success(_) as result:
                    return result

        return Failure(Exception(f"No match for {lookup_type!r} was found in the repository"))

    def get(self, lookup_type: Type[T]) -> T | None:
        """Gets an object from the repository, creating it if it doesn't exist and a provider is found that supports it,
        otherwise it will return None."""
        match self.find(lookup_type):
            case Success(result):
                return result
            case Failure(_):
                return self.create(lookup_type)
