from typing import Callable, Generic, TypeVar

from bevy.options import Option, Null, Value
from bevy.repository_cache import RepositoryCache as _RepositoryCache

_K = TypeVar("_K")
_V = TypeVar("_V")
Factory = Callable[[], _V]


class NotFound(Null):
    """Null option for when a key isn't found in a provider's cache."""


class NotSupported(Null):
    """Null option for when a key isn't supported by a provider."""


class Provider(Generic[_K, _V]):
    """The base provider type offers simple implementations of all methods that a provider should have. It does not
    offer any way to create new instances in the cache, so it shouldn't be considered a fully functional provider type.
    It is necessary for subclasses implement their own `factory` method to add support for this missing functionality.

    Every provider stores a reference to the repository it is attached to and a key/value cache for storing instances
    that it creates.
    """

    def create(self, key: _K, cache: _RepositoryCache[_K, _V]) -> Option[_V]:
        """Uses a factory function provided by the provider's factory method to get an instance that adheres to the type
        _V and that corresponds to the key. A Null option (NotSupported) is returned when no factory is available,
        otherwise a Value option containing the factory's return is returned.
        """
        match self.factory(key, cache):
            case Value(factory) if self.supports(key, cache):
                cache[key] = factory()
                return Value(cache[key])
            case _:
                return NotSupported(f"{type(self)!r} does not support {key!r}")

    def factory(self, key: _K, cache: _RepositoryCache[_K, _V]) -> Option[Factory]:
        """The base provider returns a Null option as it does not support creating new instances that adhere to the type
        _V. This method should be overriden by base classes to create or lookup instances as appropriate that are
        returned as Value options.
        """
        return Null(f"{type(self)!r} does not support creating instances of {key!r}")

    def find(self, key: _K, cache: _RepositoryCache[_K, _V]) -> Option[_V]:
        """Searches the cache for an instance that adheres to the type _V and that corresponds to the key. When a match
        is found, a Value option containing the instance is returned, otherwise a Null option (NotFound) is returned.
        """
        try:
            return Value(cache[key])
        except KeyError as exception:
            return NotFound(f"{type(self)!r} has no instances cached for {key!r}")

    def set(self, key: _K, value: _V, cache: _RepositoryCache[_K, _V]) -> Option[_V]:
        """Sets a value in the cache for the key only if the key is supported by the provider. A Null option
        (NotSupported) is returned when the key is not supported, otherwise a Value option containing the value placed
        in the cache is returned.
        """
        if not self.supports(key, cache):
            return NotSupported(f"{type(self)!r} does not support {key!r}")

        cache[key] = value
        return Value(value)

    def supports(self, key: _K, cache: _RepositoryCache[_K, _V]) -> bool:
        """Determines if the key is supported by the provider. Returns True if the `factory` method returns a Value
        option, False if it returned a Null option."""
        return bool(self.factory(key, cache))
