"""The context uses a few different concepts to provide a comprehensive, yet intuitive, interface for requesting
dependencies be injected into a class instance.

Most fundamentally it uses a repository to store all instances that have been injected by type that they are associated
with. When a class created by the context
"""
from __future__ import annotations
from typing import Callable, ParamSpec, Protocol, Type, TypeVar

from bevy.base_context import BaseContext
from bevy.null_context import NullContext
from bevy.provider import Provider, SharedInstanceProvider
from bevy.function_provider import FunctionProvider


P = ParamSpec("P")
T = TypeVar("T")


class ProviderAlreadyExistsInContext(Exception):
    ...


class Context(BaseContext):
    def __init__(self, parent: Context | None = None):
        self._parent = parent or NullContext()
        self._providers = []

    def add_provider(self, provider: Provider[T]) -> Provider[T]:
        if self.has_provider(provider, propagate=False):
            raise ProviderAlreadyExistsInContext(
                f"A matching provider already exists in {self}\n"
                f"-   Adding:  {provider}\n"
                f"-   Found:   {self.get_provider(provider, propagate=False)}"
            )

        bound_provider = provider.bind_to(self)
        self._providers.append(bound_provider)
        return bound_provider

    def branch(self) -> Context:
        return type(self)(self)

    def get_provider(
        self, provider: Provider[T], *, propagate: bool = True
    ) -> Provider[T]:
        if p := self._find_provider(provider):
            return p

        if propagate and self._parent.has_provider(provider):
            return self._parent.get_provider(provider)

        return self.add_provider(provider)

    def has_provider(self, provider: Provider[T], *, propagate: bool = True) -> bool:
        found = self._find_provider(provider)
        if not found and propagate:
            return self._parent.has_provider(provider)

        return bool(found)

    def get_provider_for(
        self,
        type_: Type[T],
        *,
        propagate: bool = True,
        provider_type: Protocol[Provider] = SharedInstanceProvider,
    ) -> Provider[T]:
        lookup_provider = provider_type(type_, self)
        return self.get_provider(lookup_provider, propagate=propagate)

    def add(
        self,
        instance: T,
        *,
        as_type: Type[T] = None,
        provider_type: Protocol[Provider] = SharedInstanceProvider,
    ):
        self.add_provider(
            provider_type(
                type(instance) if as_type is None else as_type, self, use=instance
            )
        )

    def bind(
        self,
        func: Callable[P, T],
        *,
        propagate: bool = True,
        provider_type: Protocol[Provider] = FunctionProvider,
    ) -> Callable[P, T]:
        provider = self.get_provider_for(
            func, propagate=propagate, provider_type=provider_type
        )
        return provider.get_instance()

    def get(
        self,
        type_: Type[T],
        *,
        propagate: bool = True,
        provider_type: Protocol[Provider] = SharedInstanceProvider,
        args: list | None = None,
        kwargs: dict | None = None,
    ) -> T:
        provider = self.get_provider_for(
            type_, propagate=propagate, provider_type=provider_type
        )
        return provider.get_instance(*args or [], **kwargs or {})

    def has(
        self,
        type_: Type[T],
        *,
        propagate: bool = True,
        provider_type: Protocol[Provider] = SharedInstanceProvider,
    ) -> T:
        lookup_provider = provider_type(type_, self)
        return self.has_provider(lookup_provider, propagate=propagate)

    def _find_provider(self, provider: Provider[T]) -> Provider[T] | None:
        for p in self._providers:
            if p == provider:
                return p

        return
