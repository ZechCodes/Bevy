from __future__ import annotations
from typing import cast, Generic, Sequence, Type, TypeVar

from bevy.providers.protocol import ProviderProtocol
import bevy.context.abstract_context as bc


ProviderType = TypeVar("ProviderType", bound=Type[ProviderProtocol])


class ProviderBuilder(Generic[ProviderType]):
    __match_args__ = "providers", "args", "kwargs"

    def __init__(self, provider: ProviderType, *args, **kwargs):
        self.provider = provider
        self.args = args
        self.kwargs = kwargs

    def bind(self, context: bc.AbstractContext) -> ProviderBuilder[ProviderType]:
        return ProviderBuilder(self._bind(context), *self.args, **self.kwargs)

    def _bind(
        self,
        context: bc.AbstractContext
    ) -> ProviderType:
        if self.provider.__bevy_context__ is context:
            return self.provider

        return self._create_bound_provider_type(context)

    def create_and_insert(self, providers: Sequence[ProviderProtocol]) -> Sequence[ProviderProtocol]:
        return self.provider.create_and_insert(providers, *self.args, **self.kwargs)

    def _create_bound_provider_type(self, context: bc.AbstractContext) -> ProviderType:
        return cast(
            ProviderType,
            type(
                self.provider.__name__,
                (self.provider,),
                {
                    "__bevy_context__": context
                }
            )
        )

    @classmethod
    def create(cls, provider: ProviderType | ProviderBuilder, *args, **kwargs) -> ProviderBuilder:
        match provider:
            case ProviderBuilder():
                return provider

        return ProviderBuilder(provider, *args, **kwargs)