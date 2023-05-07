from typing import Generic, TypeVar, Type

from bevy.contextvar import ContextVarDefaultFactory as _ContextVarDefaultFactory
from bevy.options import Option, Value, Null
from bevy.providers.provider import Provider
from bevy.repository_cache import RepositoryCache as _RepositoryCache

_K = TypeVar("_K")
_V = TypeVar("_V")


class _NullRepository(Generic[_K, _V]):
    """The Null Repository provides dead end null behavior. It is intended solely to simplify the propagation logic when
    searching for cached dependencies. It should only exist at the top of the repository branching tree to stop\
    propagation. It is not intended for use beyond that case."""

    def add_providers(self, *providers: Type[Provider[_K, _V]]):
        return

    def branch(self) -> "_NullRepository[_K, _V]":
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


class Repository(_NullRepository[_K, _V]):
    """The Bevy repository manages instance providers and caching the results that the providers create."""

    _bevy_repository: "_ContextVarDefaultFactory[Repository[_K, _V]]" = (
        _ContextVarDefaultFactory("bevy_context", default=lambda: Repository.factory())
    )

    def __init__(
        self,
        parent: "Repository | None" = None,
        *,
        providers: tuple[Provider[_K, _V]] = (),
    ):
        self._parent = parent or _NullRepository()
        self._providers: dict[Provider[_K, _V], _RepositoryCache[_K, _V]] = {}

        self.add_providers(*providers)

    def add_providers(self, *providers: Provider[_K, _V]):
        """Adds providers to the repository. These providers will be used to lookup and create instances that will be
        stored and returned by the repository."""
        self._providers.update(
            (provider, _RepositoryCache(self))
            for provider in providers
            if provider not in self._providers
        )

    def branch(self) -> "Repository[_K, _V]":
        """Creates a new repository that inherits the providers from the current repository. Dependencies not found on
        the new repository can be propagated to the branched parent repository. This allows the branch repository to
        inherit dependencies from the parent repository and protects the parent from changes to the branch.
        """
        return type(self)(parent=self, providers=(*self._providers,))

    def create(self, key: _K) -> Option[_V]:
        """Attempts to create an instance that adheres to the type _V and that corresponds to the key by looking for a
        provider that supports the key. Returns a Null option when no provider is found for the key, otherwise returns a
        Value option containing the instance created by the provider."""
        for provider, repo in self._providers.items():
            match provider.create(key, repo):
                case Value(result):
                    return Value(result)

        return Null(f"No providers supported the {key!r}")

    def find(self, key: _K, *, allow_propagation: bool = True) -> Option[_V]:
        """Searches all providers for a cached instance that adheres to the type _V and that corresponds to the key.
        A Value option containing the matching instance is returned, when no match is found a Null option is returned.

        When `allow_propagation` is set to True (default) this will search any parent repositories for matching cached
        values.
        """
        for provider, repo in self._providers.items():
            match provider.find(key, repo):
                case Value() as result:
                    return result

        if allow_propagation:
            match self._parent.find(key):
                case Value() as result:
                    return result

        return Null(f"No match for {key!r} was found in the repository")

    def fork_context(self) -> "Repository[_K, _V]":
        """Branches the repository and sets the branch as the repository for the current context."""
        branch = self.branch()
        self.set_repository(branch)
        return branch

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
        for provider, repo in self._providers.items():
            match provider.set(key, value, repo):
                case Value(cached_value):
                    return Value(cached_value)

        return Null()

    @classmethod
    def factory(cls) -> "Repository[_K, _V]":
        from bevy.providers import AnnotatedProvider, TypeProvider

        repository = cls()
        repository.add_providers(AnnotatedProvider(), TypeProvider())
        return repository

    @classmethod
    def get_repository(cls: "Type[Repository[_K, _V]]") -> "Repository[_K, _V]":
        """Retrieves the repository instance that is assigned to the current context."""
        return cls._bevy_repository.get()

    @classmethod
    def set_repository(cls, repository: "Repository[_K, _V]"):
        """Assigns a new repository instance to the current context."""
        cls._bevy_repository.set(repository)


get_repository = Repository.get_repository
