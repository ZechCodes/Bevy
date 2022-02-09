from __future__ import annotations
from typing import Generic, ParamSpec, Type, TypeVar
import bevy


T = TypeVar("T")
P = ParamSpec("P")


class Constructor(Generic[T]):
    def __init__(self, instance_type: Type[T], *args: P.args, **kwargs: P.kwargs):
        self.type = instance_type
        self.args = args
        self.kwargs = kwargs

    def create(self, context: bevy.Context) -> T:
        return context.bind(self.type)(*self.args, **self.kwargs)
