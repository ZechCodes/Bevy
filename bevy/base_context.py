from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Sequence

import bevy.provider as p


KeyObject = TypeVar("KeyObject")
ValueObject = TypeVar("ValueObject")
T = TypeVar("T")


class BaseContext(ABC):
    @abstractmethod
    def add(
        self,
        obj: ValueObject,
        *,
        use_as: KeyObject | None = None,
        propagate: bool = True
    ):
        ...

    @abstractmethod
    def add_provider(
        self,
        provider: Type[p.ProviderProtocol],
        *args,
        __provider__: p.ProviderProtocol | None = None,
        **kwargs
    ):
        ...

    @abstractmethod
    def bind(self, obj: KeyObject, *, propagate: bool = True) -> KeyObject:
        ...

    @abstractmethod
    def branch(self) -> BaseContext:
        ...

    @abstractmethod
    def create(
        self,
        obj: KeyObject,
        *args,
        add_to_context: bool = False,
        propagate: bool = True,
        **kwargs
    ) -> ValueObject:
        ...

    @abstractmethod
    def get(
        self,
        obj: KeyObject,
        default: ValueObject | T | None = None,
        *, propagate: bool = True
    ) -> ValueObject | T | None:
        ...

    @abstractmethod
    def get_provider_for(
        self,
        obj: KeyObject,
        *,
        propagate: bool = True
    ) -> p.ProviderProtocol[KeyObject, ValueObject] | None:
        ...

    @abstractmethod
    def has(self, obj: KeyObject, *, propagate: bool = True) -> bool:
        ...

    @abstractmethod
    def has_provider_for(self, obj: KeyObject, *, propagate: bool = True) -> bool:
        ...
