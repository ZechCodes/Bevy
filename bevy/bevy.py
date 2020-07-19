from __future__ import annotations
from bevy.context import Context
from typing import Type


class Bevy:
    def __new__(cls: Type[Bevy], *args, **kwargs) -> Bevy:
        return Context().create(cls, *args, **kwargs)
