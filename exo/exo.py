from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Tuple, Type


class ExoMeta(ABCMeta):
    ...


class Exo(metaclass=ExoMeta):
    ...
