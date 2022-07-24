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
        if instance is None:
            return

        if context := getattr(instance, "__bevy_context__", None):
            return context

        return c.Context.factory()
