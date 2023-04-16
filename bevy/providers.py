from typing import Callable, Generic, TypeVar

from bevy.options import Option, Null, Value

_K = TypeVar("_K")
_V = TypeVar("_V")
Factory = Callable[[], _V]


class NotFound(Null):
    """Null option for when a key isn't found in a provider's cache."""


class NotSupported(Null):
    """Null option for when a key isn't supported by a provider."""


class Provider(Generic[_K, _V]):


    def __init__(self, repository):
        self._repository = repository
        self._cache: dict[_K, _V] = {}

    def factory(self, key: _K) -> Option[Factory]:
        """Should create a function to build an instance of the type, or returns None if the type is not supported."""
        return Null(f"{type(self)!r} does not support creating instances of {key!r}")

    def create(self, key: _K) -> Option[_V]:
        match self.factory(key):
            case Value(factory) if self.supports(key):
                self._cache[key] = factory()
                return Value(self._cache[key])
            case _:
                return NotSupported(f"{type(self)!r} does not support {key!r}")

    def find(self, key: _K) -> Option[_V]:
        try:
            return Value(self._cache[key])
        except KeyError as exception:
            return NotFound(f"{type(self)!r} has no instances cached for {key!r}")

    def set(self, key: _K, value: _V) -> Option[_V]:
        if not self.supports(key):
            return NotSupported(f"{type(self)!r} does not support {key!r}")

        self._cache[key] = value
        return Value(value)

    def supports(self, key: _K) -> bool:
        return bool(self.factory(key))
