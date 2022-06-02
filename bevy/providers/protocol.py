from __future__ import annotations
from typing import overload, Protocol, Sequence, TypeVar

import bevy.context.abstract_context as bc


KeyObject = TypeVar("KeyObject")
ValueObject = TypeVar("ValueObject")
T = TypeVar("T")


class ProviderProtocol(Protocol[KeyObject, ValueObject]):
    __bevy_context__: bc.AbstractContext

    def add(self, obj: ValueObject, *, use_as: KeyObject | None = None):
        ...

    def bind_to_context(self, obj: KeyObject, contex) -> KeyObject:
        ...

    def create(self, obj: KeyObject, *args, add: bool = False, **kwargs) -> ValueObject:
        ...

    @overload
    def get(self, obj: KeyObject, default: ValueObject) -> ValueObject:
        ...

    @overload
    def get(self, obj: KeyObject, default: None = None) -> ValueObject | None:
        ...

    @overload
    def get(self, obj: KeyObject, default: T) -> ValueObject | T:
        ...

    def get(self, obj: KeyObject, default: ValueObject | T | None = None) -> ValueObject | T | None:
        ...

    def has(self, obj: KeyObject) -> bool:
        ...

    def supports(self, obj: KeyObject) -> bool:
        ...

    @classmethod
    def create_and_insert(
        cls,
        providers: Sequence[ProviderProtocol],
        *args,
        **kwargs
    ) -> Sequence[ProviderProtocol]:
        ...