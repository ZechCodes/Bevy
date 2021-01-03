from __future__ import annotations
from bevy.context import Context
from bevy.factory import FactoryAnnotation
from typing import Any, Dict, Optional, Tuple, Type, Union


class InjectableMeta(type):
    def __call__(cls: Type[Injectable], *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Injectable:
        return Context().create(cls, *args, **kwargs)


class Injectable(metaclass=InjectableMeta):
    ...
