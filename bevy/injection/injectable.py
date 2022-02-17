from __future__ import annotations
from typing import Protocol
import bevy.injection.context as bevy_context


class Injectable(Protocol):
    __bevy_context__: bevy_context.Context
