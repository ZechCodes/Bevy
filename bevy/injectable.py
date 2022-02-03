from __future__ import annotations
from typing import Protocol
import bevy.context


class Injectable(Protocol):
    __bevy_context__: bevy.context.Context
