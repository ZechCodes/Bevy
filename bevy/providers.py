from abc import ABC, abstractmethod
from typing import Callable, Generic, TypeVar

from bevy.options import Option, Value
from bevy.results import Result, result

_K = TypeVar("_K")
_V = TypeVar("_V")
Factory = Callable[[], _V]


class _MessageResult(Result):
    __match_args__ = ("message",)

    def __init__(self, message: str):
        self.message = message

    def __bool__(self):
        return False


class NotFound(_MessageResult):
    ...


class NotSupported(_MessageResult):
    ...


class Provider(Generic[_K, _V], ABC):
    def __init__(self, repository):
        self._repository = repository
        self._cache: dict[_K, _V] = {}

    @abstractmethod
    def factory(self, key: _K) -> Option[Factory]:
        """Should create a function to build an instance of the type, or returns None if the type is not supported."""

    @result
    def create(self, key: _K) -> _V | NotSupported:
        match self.factory(key):
            case Value(factory):
                self._cache[key] = factory()
                return self._cache[key]
            case _:
                return NotSupported(f"{type(self)!r} does not support {key!r}")

    @result
    def find(self, key: _K) -> _V | NotFound:
        try:
            return self._cache[key]
        except KeyError as exception:
            return NotFound(f"{type(self)!r} has no instances cached for {key!r}")

    @result
    def set(self, key: _K, value: _V) -> _V | Result:
        if not self.supports(key):
            return NotSupported(f"{type(self)!r} does not support {key!r}")

        self._cache[key] = value
        return value

    def supports(self, key: _K) -> bool:
        return bool(self.factory(key))
