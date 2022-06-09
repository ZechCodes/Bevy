from typing import Sequence

from bevy.providers.protocol import ProviderProtocol


@classmethod
def high_priority(
    cls, providers: Sequence[ProviderProtocol], *args, **kwargs
) -> Sequence[ProviderProtocol]:
    return cls(*args, **kwargs), *providers


@classmethod
def low_priority(
    cls, providers: Sequence[ProviderProtocol], *args, **kwargs
) -> Sequence[ProviderProtocol]:
    return *providers, cls(*args, **kwargs)
