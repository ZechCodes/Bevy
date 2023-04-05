from bevy.results import Success, Failure, Result, ResultBuilder
from typing import Callable, Type, TypeVar
from abc import ABC, abstractmethod


T = TypeVar("T")
Builder = Callable[[], T]


class Provider(ABC):
    def __init__(self, repository):
        self._repository = repository
        self._cache: dict[Type[T], T] = {}

    @abstractmethod
    def builder(self, new_type: Type[T]) -> Builder | None:
        """Should create a function to build an instance of the type, or returns None if the type is not supported."""

    def create(self, new_type: Type[T]) -> Result[T]:
        with ResultBuilder() as (result_builder, set_result):
            if (builder := self.builder(new_type)) is None:
                raise Exception(f"The provider does not support {new_type!r}")

            self._cache[new_type] = set_result(builder())

        return result_builder.result

    def find(self, lookup_type: Type[T]) -> Result[T]:
        with ResultBuilder() as (builder, set_result):
            try:
                set_result(self._cache[lookup_type])
            except KeyError as exception:
                raise Exception(f"Provider had no instances cached for {lookup_type!r}") from exception

        return builder.result
