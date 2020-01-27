from __future__ import annotations
from typing import TypeVar


ExoRepository = TypeVar("ExoRepository", bound="Repository")


class Repository:
    ...
