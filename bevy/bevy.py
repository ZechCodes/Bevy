from __future__ import annotations
from bevy.context import Context
from bevy.factory import FactoryAnnotation
from typing import Any, Dict, Optional, Tuple, Type, Union


class BevyMeta(type):
    def __call__(cls: Type[Bevy], *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Bevy:
        return Context().create(cls, *args, **kwargs)


class Bevy(metaclass=BevyMeta):
    ...
