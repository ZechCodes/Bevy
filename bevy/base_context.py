from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type, TypeVar

import bevy.provider as p


T = TypeVar("T")


class BaseContext(ABC):
    @abstractmethod
    def add_provider(self, provider: p.Provider[T]):
        ...

    @abstractmethod
    def branch(self) -> BaseContext:
        ...

    @abstractmethod
    def get_provider(
        self, provider: p.Provider[T], *, propagate: bool
    ) -> p.Provider[T] | None:
        ...

    @abstractmethod
    def get_provider_for(
        self, type_: Type[T], *, propagate: bool
    ) -> p.Provider[T] | None:
        ...

    @abstractmethod
    def get(self, type_: Type[T], *, propagate: bool = True) -> T | None:
        ...

    @abstractmethod
    def has_provider(self, provider: p.Provider[T], *, propagate: bool) -> bool:
        ...
