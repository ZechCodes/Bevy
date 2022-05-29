from __future__ import annotations
from typing import TypeVar, Protocol, overload, Sequence

from bevy.inject import Dependencies
from bevy.sentinel import sentinel


KeyObject = TypeVar("KeyObject")
ValueObject = TypeVar("ValueObject")
T = TypeVar("T")


NOT_FOUND = sentinel("NOT_FOUND")


class ProviderProtocol(Protocol[KeyObject, ValueObject]):
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
        __provider__: ProviderProtocol | None = None,
        **kwargs
    ) -> Sequence[ProviderProtocol]:
        ...


class InstanceMatchingProvider(ProviderProtocol, Dependencies):
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
        __provider__: ProviderProtocol | None = None,
        **kwargs
    ) -> Sequence[ProviderProtocol]:
        return __provider__ or cls(*args, **kwargs), *providers


class TypeMatchingProvider(ProviderProtocol, Dependencies):
    def __init__(self, *_, **__):
        super().__init__()
        self._repository = {}

    def add(self, obj: ValueObject, *, use_as: KeyObject | None = None):
        key = use_as or type(obj)
        self._repository[key] = obj

    def bind_to_context(self, obj: KeyObject | type, context) -> KeyObject | type:
        return type(obj.__name__, (object,), {"__bevy__": context})

    def create(self, obj: KeyObject, *args, add: bool = False, **kwargs) -> ValueObject:
        value = self.__bevy__.bind(obj)(*args, **kwargs)
        if add:
            self.add(value)

        return value

    def get(self, obj: KeyObject, default: ValueObject | T | None = None) -> ValueObject | T | None:
        for key, value in self._repository.items():
            if obj is key or (isinstance(obj, type) and (issubclass(obj, key) and issubclass(key, obj))):
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
        __provider__: ProviderProtocol | None = None,
        **kwargs
    ) -> Sequence[ProviderProtocol]:
        return *providers, __provider__ or cls(*args, **kwargs)
