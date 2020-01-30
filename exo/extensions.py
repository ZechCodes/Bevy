from __future__ import annotations
from abc import abstractmethod
from exo.composables import Composable
from typing import Any, TypeVar


ExoExtension = TypeVar("ExoExtension", bound="AbstractExtension")


class AbstractExtension(Composable):
    ...


class Extension(AbstractExtension):
    ...
