from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, overload, Generic, Sequence, TypeVar

import bevy.context.abstract_context as bc
import bevy.providers.injection_priority_helpers as priority_helpers


ProviderInjectorFunction = Callable[
    [Sequence["BaseProvider"]], Sequence["BaseProvider"]
]
KeyObject = TypeVar("KeyObject")
ValueObject = TypeVar("ValueObject")
T = TypeVar("T")


class BaseProvider(ABC, Generic[KeyObject, ValueObject]):
    __bevy_context__: bc.AbstractContext

    def __init_subclass__(
        cls, *, priority: ProviderInjectorFunction | str | None = None, **kwargs
    ):
        priority_injectors = {
            "high": priority_helpers.high_priority,
            "low": priority_helpers.low_priority,
        }
        if isinstance(priority, str) and priority in priority_injectors:
            cls.create_and_insert = priority_injectors[priority]

        elif callable(priority):
            cls.create_and_insert = priority

    @abstractmethod
    def add(self, obj: ValueObject, *, use_as: KeyObject | None = None):
        ...

    @abstractmethod
    def bind_to_context(self, obj: KeyObject, contex) -> KeyObject:
        ...

    @abstractmethod
    def create(self, obj: KeyObject, *args, add: bool = False, **kwargs) -> ValueObject:
        ...

    @abstractmethod
    @overload
    def get(self, obj: KeyObject, default: ValueObject) -> ValueObject:
        ...

    @overload
    def get(self, obj: KeyObject, default: None = None) -> ValueObject | None:
        ...

    @overload
    def get(self, obj: KeyObject, default: T) -> ValueObject | T:
        ...

    @abstractmethod
    def get(
        self, obj: KeyObject, default: ValueObject | T | None = None
    ) -> ValueObject | T | None:
        ...

    @abstractmethod
    def has(self, obj: KeyObject) -> bool:
        ...

    @abstractmethod
    def supports(self, obj: KeyObject) -> bool:
        ...

    @classmethod
    def create_and_insert(
        cls, providers: Sequence[BaseProvider], *args, **kwargs
    ) -> Sequence[BaseProvider]:
        ...
