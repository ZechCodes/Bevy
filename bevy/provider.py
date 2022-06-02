from __future__ import annotations
from typing import cast, Generic, Type, TypeVar, Protocol, overload, Sequence

from bevy.inject import BevyInject
from bevy.sentinel import sentinel
import bevy.base_context as base_context


KeyObject = TypeVar("KeyObject")
ValueObject = TypeVar("ValueObject")
ProviderType = TypeVar("ProviderType", bound="Protocol[ProviderProtocol]")
T = TypeVar("T")


NOT_FOUND = sentinel("NOT_FOUND")


class ProviderBuilder(Generic[ProviderType]):
    __match_args__ = "provider", "args", "kwargs"

    def __init__(self, provider: ProviderType, *args, **kwargs):
        self.provider = provider
        self.args = args
        self.kwargs = kwargs

    def bind(self, context: base_context.BaseContext) -> ProviderBuilder[ProviderType]:
        return ProviderBuilder(self._bind(context), *self.args, **self.kwargs)

    def _bind(
        self,
        context: base_context.BaseContext
    ) -> ProviderType:
        if self.provider.__bevy_context__ is context:
            return self.provider

        return self._create_bound_provider_type(context)

    def create_and_insert(self, providers: Sequence[ProviderProtocol]) -> Sequence[ProviderProtocol]:
        return self.provider.create_and_insert(providers, *self.args, **self.kwargs)

    def _create_bound_provider_type(self, context: base_context.BaseContext) -> ProviderType:
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
    def create(cls, provider: Type[ProviderProtocol] | ProviderBuilder, *args, **kwargs) -> ProviderBuilder:
        match provider:
            case ProviderBuilder(existing_provider):
                return provider

        return ProviderBuilder(provider, *args, **kwargs)


class ProviderProtocol(Protocol[KeyObject, ValueObject]):
    __bevy_context__: base_context.BaseContext

    def add(self, obj: ValueObject, *, use_as: KeyObject | None = None):
        ...

    def bind_to_context(self, obj: KeyObject, contex) -> KeyObject:
        ...

    def create(self, obj: KeyObject, *args, add: bool = False, **kwargs) -> ValueObject:
        ...

    @overload
    def get(self, obj: KeyObject, default: ValueObject) -> ValueObject:
        ...

    @overload
    def get(self, obj: KeyObject, default: None = None) -> ValueObject | None:
        ...

    @overload
    def get(self, obj: KeyObject, default: T) -> ValueObject | T:
        ...

    def get(self, obj: KeyObject, default: ValueObject | T | None = None) -> ValueObject | T | None:
        ...

    def has(self, obj: KeyObject) -> bool:
        ...

    def supports(self, obj: KeyObject) -> bool:
        ...

    @classmethod
    def create_and_insert(
        cls,
        providers: Sequence[ProviderProtocol],
        *args,
        **kwargs
    ) -> Sequence[ProviderProtocol]:
        ...


class InstanceMatchingProvider(ProviderProtocol, BevyInject):
    def __init__(self, *_, **__):
        super().__init__()
        self._repository = {}

    def add(self, obj: ValueObject, *, use_as: KeyObject | None = None):
        self._repository[use_as or obj] = obj

    def bind_to_context(self, obj: KeyObject, context) -> KeyObject:
        raise Exception("Cannot bind instances to a context")

    def create(self, obj: KeyObject, *args, add: bool = False, **kwargs) -> ValueObject:
        if add:
            self.add(obj)

        return obj

    def get(self, obj: KeyObject, default: ValueObject | T | None = None) -> ValueObject | T | None:
        for key, value in self._repository.items():
            if obj is key:
                return value

        return default

    def has(self, obj: KeyObject) -> bool:
        return self.get(obj, NOT_FOUND) is not NOT_FOUND

    def supports(self, obj: KeyObject) -> bool:
        return not isinstance(obj, type)

    @classmethod
    def create_and_insert(
        cls,
        providers: Sequence[ProviderProtocol],
        *args,
        **kwargs
    ) -> Sequence[ProviderProtocol]:
        return cls(*args, **kwargs), *providers


class TypeMatchingProvider(ProviderProtocol, BevyInject):
    def __init__(self, *_, **__):
        super().__init__()
        self._repository = {}

    def add(self, obj: ValueObject, *, use_as: KeyObject | None = None):
        key = use_as or type(obj)
        self._repository[key] = obj

    def bind_to_context(self, obj: KeyObject | type, context) -> KeyObject | type:
        return type(obj.__name__, (obj,), {"__bevy_context__": context})

    def create(self, obj: KeyObject, *args, add: bool = False, **kwargs) -> ValueObject:
        value = self.bevy.bind(obj)(*args, **kwargs)
        if add:
            self.add(value)

        return value

    def get(self, obj: KeyObject, default: ValueObject | T | None = None) -> ValueObject | T | None:
        for key, value in self._repository.items():
            if obj is key or (isinstance(obj, type) and (issubclass(obj, key) or issubclass(key, obj))):
                return value

        return default

    def has(self, obj: KeyObject) -> bool:
        return self.get(obj, NOT_FOUND) is not NOT_FOUND

    def supports(self, obj: KeyObject) -> bool:
        return isinstance(obj, type)

    @classmethod
    def create_and_insert(
        cls,
        providers: Sequence[ProviderProtocol],
        *args,
        **kwargs
    ) -> Sequence[ProviderProtocol]:
        return *providers, cls(*args, **kwargs)
