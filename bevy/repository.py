from typing import Generic, TypeVar, Type

from bevy.contextvar import ContextVarDefaultFactory as _ContextVarDefaultFactory
from bevy.options import Option, Value, Null
from bevy.providers.base import Provider

_K = TypeVar("_K")
_V = TypeVar("_V")


class NullRepository(Generic[_K, _V]):
    def add_providers(self, *providers: Type[Provider[_K, _V]]):
        return

    def branch(self) -> "NullRepository":
        return self

    def create(self, key: _K) -> Option[_V]:
        return Null()

    def find(self, key: _K, *, allow_propagation: bool = True) -> Option[_V]:
        return Null()

    def get(
        self, key: _K, default: _V | None = None, *, allow_propagation: bool = True
    ) -> _V:
        return

    def set(self, key: _K, value: _V) -> Option[_V]:
        return Null()


class Repository(NullRepository[_K, _V]):
    """The Bevy repository manages instance providers and caching the results that the providers create."""

    _bevy_repository: "_ContextVarDefaultFactory[Repository[_K, _V]]" = (
        _ContextVarDefaultFactory("bevy_context", default=lambda: Repository())
    )

    def __init__(self, parent: "Repository | None" = None):
        self._parent = parent or NullRepository()
        self._providers: list[Provider[_K, _V]] = []

    def add_providers(self, *providers: Type[Provider[_K, _V]]):
        """Creates providers and adds them to the repository. These providers will be used to lookup and create
        instances that will be stored and returned by the repository."""
        self._providers.extend(provider(self) for provider in providers)

    def branch(self) -> "Repository":
        branch = type(self)(self)

        providers = (provider.get_clone_factory() for provider in self._providers)
        branch.add_providers(*providers)

        return branch

    def create(self, key: _K) -> Option[_V]:
        """Attempts to create an instance that adheres to the type _V and that corresponds to the key by looking for a
        provider that supports the key. Returns a Null option when no provider is found for the key, otherwise returns a
        Value option containing the instance created by the provider."""
        for provider in self._providers:
            match provider.create(key):
                case Value(result):
                    return Value(result)

        return Null(f"No providers supported the {key!r}")

    def find(self, key: _K, *, allow_propagation: bool = True) -> Option[_V]:
        """Searches all providers for a cached instance that adheres to the type _V and that corresponds to the key.
        A Value option containing the matching instance is returned, when no match is found a Null option is returned.

        When `allow_propagation` is set to True (default) this will search any parent repositories for matching cached
        values.
        """
        for provider in self._providers:
            match provider.find(key):
                case Value() as result:
                    return result

        if allow_propagation:
            match self._parent.find(key):
                case Value() as result:
                    return result

        return Null(f"No match for {key!r} was found in the repository")

    def get(
        self, key: _K, default: _V | None = None, *, allow_propagation: bool = True
    ) -> _V:
        """Attempts to get an instance adhering to the type _V that corresponds to the key. It first attempts to find a
        matching instance that is cached on any provider. If no cached instances are found, it attempts to create an
        instance that is then cached. When a match is found or created it is returned, otherwise the default is used.

        When `allow_propagation` is set to True (default) this will search any parent repositories for matching cached
        values. If no matches are found on this repository or any of it's parents, it will attempt to create the value
        in this repository's cache.
        """
        match self.find(key, allow_propagation=allow_propagation):
            case Value(result):
                return result
            case Null():
                return self.create(key).value_or(default)

    def set(self, key: _K, value: _V) -> Option[_V]:
        """Attempts to cache a value. A Null option is returned when no providers support the key, otherwise a Value
        option containing the value that was placed in the cache is returned."""
        for provider in self._providers:
            match provider.set(key, value):
                case Value(cached_value):
                    return Value(cached_value)

        return Null()

    @classmethod
    def get_repository(cls: "Type[Repository[_K, _V]]") -> "Repository[_K, _V]":
        """Retrieves the repository instance that is assigned to the current context."""
        return cls._bevy_repository.get()

    @classmethod
    def set_repository(cls, repository: "Repository[_K, _V]"):
        """Assigns a new repository instance to the current context."""
        cls._bevy_repository.set(repository)


get_repository = Repository.get_repository
