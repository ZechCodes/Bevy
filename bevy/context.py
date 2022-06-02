"""The context uses a few different concepts to provide a comprehensive, yet intuitive, interface for requesting
dependencies be injected into a class instance.

Most fundamentally it uses a repository to store all instances that have been injected by type that they are associated
with. When a class created by the context
"""
from __future__ import annotations
from typing import ParamSpec, Protocol, Type, TypeVar, Sequence

from bevy.base_context import BaseContext
from bevy.null_context import NullContext
from bevy.provider import ProviderBuilder, ProviderProtocol, InstanceMatchingProvider, TypeMatchingProvider
from bevy.sentinel import sentinel


P = ParamSpec("P")
T = TypeVar("T")
KeyObject = TypeVar("KeyObject")
ValueObject = TypeVar("ValueObject")


ProviderConstructor = ProviderBuilder | Type[ProviderProtocol]


NOT_FOUND = sentinel("NOT_FOUND")


class NoSupportingProviderFoundInContext(Exception):
    ...


class Context(BaseContext):
    def __init__(self, *providers: ProviderConstructor, parent: Context | None = None):
        self._parent = parent or NullContext()
        self._providers, self._provider_constructors = self._build_providers(providers)

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
        provider: Protocol[ProviderProtocol],
        *args,
        **kwargs
    ):
        builder = ProviderBuilder.create(provider, *args, **kwargs)
        self._providers = builder.bind(self).create_and_insert(self._providers)
        self._provider_constructors.append(builder)

    def bind(self, obj: KeyObject, *, propagate: bool = True) -> KeyObject:
        provider = self.get_provider_for(obj, propagate=propagate)
        if not provider:
            raise NoSupportingProviderFoundInContext(
                f"No provider was found in the context that supports the object. {obj=} {propagate=}"
            )

        return provider.bind_to_context(obj, self)

    def branch(self) -> Context:
        return type(self)(*self._provider_constructors, parent=self)

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
        provider_types: Sequence[ProviderConstructor]
    ) -> tuple[Sequence[ProviderProtocol], list[ProviderBuilder]]:
        if not provider_types:
            return self._build_providers((InstanceMatchingProvider, TypeMatchingProvider))

        return self._build_providers_from_provider_types(provider_types)

    def _build_providers_from_provider_types(
        self,
        provider_types: Sequence[ProviderConstructor]
    ) -> tuple[Sequence[ProviderProtocol], list[ProviderBuilder]]:
        builders = []
        providers = ()
        for provider in provider_types:
            builders.append(builder := ProviderBuilder.create(provider))
            providers = builder.bind(self).create_and_insert(providers)

        return providers, builders

    def _find_provider(self, obj: KeyObject) -> ProviderProtocol | None:
        for provider in self._providers:
            if provider.supports(obj):
                return provider
