from __future__ import annotations
from typing import Sequence

import bevy.providers.base as provider_base


@classmethod
def high_priority(
    cls, providers: Sequence[provider_base.BaseProvider], *args, **kwargs
) -> Sequence[provider_base.BaseProvider]:
    return cls(*args, **kwargs), *providers


@classmethod
def low_priority(
    cls, providers: Sequence[provider_base.BaseProvider], *args, **kwargs
) -> Sequence[provider_base.BaseProvider]:
    return *providers, cls(*args, **kwargs)
