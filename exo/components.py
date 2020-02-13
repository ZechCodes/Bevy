from __future__ import annotations
from abc import abstractmethod
from exo.composables import Composable
from typing import Any, TypeVar


ExoComponent = TypeVar("ExoComponent", bound="AbstractComponent")


class AbstractComponent(Composable):
    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        return


class Component(AbstractComponent):
    ...
