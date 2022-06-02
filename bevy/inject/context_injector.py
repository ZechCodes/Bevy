from __future__ import annotations
from functools import cache
from typing import overload, Type, TypeVar

import bevy.context.abstract_context as bc
import bevy.context as c


T = TypeVar("T")


class ContextInjector:
    @overload
    def __get__(self, instance: None, owner: Type[T]) -> None:
        ...

    @overload
    def __get__(self, instance: T, owner: Type[T]) -> bc.AbstractContext:
        ...

    @cache
    def __get__(self, instance: T | None, owner: Type[T]) -> bc.AbstractContext | None:
        if not instance:
            return

        if instance.__bevy_context__:
            return instance.__bevy_context__

        return c.Context()
