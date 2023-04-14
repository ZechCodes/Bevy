from bevy.results import Result, ResultBuilder
from typing import Callable, Generic, TypeVar
from abc import ABC, abstractmethod


_K = TypeVar("_K")
_V = TypeVar("_V")
Builder = Callable[[], _V]


class Provider(Generic[_K, _V], ABC):
    def __init__(self, repository):
        self._repository = repository
        self._cache: dict[_K, _V] = {}

    def add(self, key: _K, value: _V) -> Result[bool]:
        with ResultBuilder() as (result_builder, set_result):
            if (builder := self.builder(key)) is None:
                raise Exception(f"The provider does not support {key!r}")

            self._cache[key] = value
            set_result(True)

        return result_builder.result

    @abstractmethod
    def builder(self, key: _K) -> Builder | None:
        """Should create a function to build an instance of the type, or returns None if the type is not supported."""

    def create(self, key: _K) -> Result[_V]:
        with ResultBuilder() as (result_builder, set_result):
            if (builder := self.builder(key)) is None:
                raise Exception(f"The provider does not support {key!r}")

            self._cache[key] = set_result(builder())

        return result_builder.result

    def find(self, key: _K) -> Result[_V]:
        with ResultBuilder() as (builder, set_result):
            try:
                set_result(self._cache[key])
            except KeyError as exception:
                raise Exception(f"Provider had no instances cached for {key!r}") from exception

        return builder.result
