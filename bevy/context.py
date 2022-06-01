"""The context uses a few different concepts to provide a comprehensive, yet intuitive, interface for requesting
dependencies be injected into a class instance.

Most fundamentally it uses a repository to store all instances that have been injected by type that they are associated
with. When a class created by the context
"""
from __future__ import annotations
from typing import ParamSpec, Type, TypeVar, Sequence

from bevy.base_context import BaseContext
from bevy.null_context import NullContext
from bevy.provider import ProviderProtocol
from bevy.sentinel import sentinel


P = ParamSpec("P")
T = TypeVar("T")
KeyObject = TypeVar("KeyObject")
ValueObject = TypeVar("ValueObject")


NOT_FOUND = sentinel("NOT_FOUND")


class NoSupportingProviderFoundInContext(Exception):
    ...


class Context(BaseContext):
    def __init__(self, *providers, parent: Context | None = None):
        self._parent = parent or NullContext()
        self._providers: Sequence[ProviderProtocol] = self._build_providers(providers)

    def add(
        self,
        obj: ValueObject,
        *,
        use_as: KeyObject | None = None,
        propagate: bool = True
    ):
        provider = self.get_provider_for(use_as or obj, propagate=propagate)
        if not provider:
            raise NoSupportingProviderFoundInContext(
                f"No provider was found in the context that supports the object being added. {obj=} {use_as=} "
                f"{propagate=}"
            )

        provider.add(obj, use_as=use_as)

    def add_provider(
        self,
        provider:
        Type[ProviderProtocol],
        *args,
        __provider__: ProviderProtocol | None = None,
        **kwargs
    ):
        self._providers = self.bind(provider).create_and_insert(
            self._providers, *args, __provider__=__provider__, **kwargs
        )

    def bind(self, obj: KeyObject, *, propagate: bool = True) -> KeyObject:
        provider = self.get_provider_for(obj, propagate=propagate)
        if not provider:
            raise NoSupportingProviderFoundInContext(
                f"No provider was found in the context that supports the object. {obj=} {propagate=}"
            )

        return provider.bind_to_context(obj, self)

    def branch(self) -> Context:
        return type(self)(parent=self)

    def create(
        self,
        obj: KeyObject,
        *args,
        add_to_context: bool = False,
        propagate: bool = True,
        **kwargs
    ) -> ValueObject:
        provider = self.get_provider_for(obj, propagate=propagate)
        return provider.create(obj, *args, add=add_to_context, **kwargs)

    def get(
        self,
        obj: KeyObject,
        default: ValueObject | T | None = None,
        *, propagate: bool = True
    ) -> ValueObject | T | None:
        provider = self.get_provider_for(obj, propagate=False)
        if provider and provider.has(obj):
            return provider.get(obj)

        if propagate:
            return self._parent.get(obj, default)

        return default

    def get_provider_for(
        self,
        obj: KeyObject,
        *,
        propagate: bool = True
    ) -> ProviderProtocol[KeyObject, ValueObject] | None:
        if p := self._find_provider(obj):
            return p

        if propagate and self._parent.has_provider_for(obj):
            return self._parent.get_provider_for(obj)

    def has(self, obj: KeyObject, *, propagate: bool = True) -> bool:
        return self.get(obj, NOT_FOUND, propagate=propagate) is not NOT_FOUND

    def has_provider_for(self, obj: KeyObject, *, propagate: bool = True) -> bool:
        return self.get_provider_for(obj, propagate=propagate) is not None

    def _build_providers(
        self,
        provider_types: Sequence[Type[ProviderProtocol] | ProviderProtocol]
    ) -> Sequence[ProviderProtocol]:
        providers = ()
        for p in provider_types:
            provider_type, provider = (p, None) if isinstance(p, type) else (type(p), p)
            providers = provider_type.add_provider(providers, __provider__=provider)

        return providers

    def _find_provider(self, obj: KeyObject) -> ProviderProtocol | None:
        for provider in self._providers:
            if provider.supports(obj):
                return provider
