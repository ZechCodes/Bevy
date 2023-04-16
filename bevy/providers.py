from abc import ABC, abstractmethod
from typing import Callable, Generic, TypeVar

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
    def factory(self, key: _K) -> Factory | None:
        """Should create a function to build an instance of the type, or returns None if the type is not supported."""

    @result
    def create(self, key: _K) -> _V | NotSupported:
        if (factory := self.factory(key)) is None:
            return NotSupported(f"{type(self)!r} does not support {key!r}")

        self._cache[key] = factory()
        return self._cache[key]

    @result
    def find(self, key: _K) -> _V | NotFound:
        try:
            return self._cache[key]
        except KeyError as exception:
            return NotFound(f"{type(self)!r} has no instances cached for {key!r}")

    @result
    def set(self, key: _K, value: _V) -> NotSupported | None:
        if self.factory(key) is None:
            return NotSupported(f"{type(self)!r} does not support {key!r}")

        self._cache[key] = value
